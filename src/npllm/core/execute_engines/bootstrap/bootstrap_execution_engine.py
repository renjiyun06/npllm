import uuid
from importlib import resources
from typing import Callable, List, Any, Dict, Tuple

from litellm import acompletion
from jinja2 import Template

from npllm.core.semantic_execute_engine import SemanticExecuteEngine
from npllm.core.semantic_call import SemanticCall
from typing import Callable, List, Any, Dict, Tuple

from npllm.utils.json_util import parse_json_str

import logging

logger = logging.getLogger(__name__)

class CacheItem:
    def __init__(self, system_prompt_template: str, user_prompt_template: str):
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template

    def check_valid(self, semantic_call: SemanticCall) -> bool:
        return True

class BootstrapExecutionEngine(SemanticExecuteEngine):
    def __init__(
        self,
        compile_model: str,
        execution_model: str,
        template_placeholder_handler: Callable[[str, List[Any], Dict[str, Any]], str]
    ):
        self._compile_model = compile_model
        self._execution_model = execution_model
        self._compile_prompt = None
        with resources.open_text("npllm.core.execute_engines.bootstrap", "compile_prompt.md") as f:
            self._compile_prompt = f.read()

        self._compilation_cache: Dict[SemanticCall, CacheItem] = {}
        self._load_compilation_cache()

        self._template_placeholder_handler = template_placeholder_handler

    def _load_compilation_cache(self):
        pass

    def _save_compilation_cache(self, semantic_call: SemanticCall, cache_item: CacheItem):
        self._compilation_cache[semantic_call] = cache_item

    async def execute(self, semantic_call: SemanticCall, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        system_prompt_template, user_prompt_template = await self._compile(semantic_call)

        system_prompt = self._template_placeholder_handler(system_prompt_template, args, kwargs)
        user_prompt = self._template_placeholder_handler(user_prompt_template, args, kwargs)

        logger.debug(f"System prompt for execution LLM: {system_prompt}")
        logger.debug(f"User prompt for execution LLM: {user_prompt}")
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await acompletion(model=self._execution_model, messages=messages)
        response_content = response.choices[0].message.content.strip()
        logger.debug(f"Raw response content from execution LLM: {response_content}")

        json_value = parse_json_str(response_content)

        value = semantic_call.return_type.pydantic_type_adapter().validate_python(json_value)
        logger.info(f"Successfully parsed the response from execution LLM for {semantic_call}")
        return value

    async def _compile(self, semantic_call: SemanticCall) -> Tuple[str, str]:
        if semantic_call in self._compilation_cache:
            cache_item = self._compilation_cache[semantic_call]
            if cache_item.check_valid(semantic_call):
                logger.info(f"Using cached compilation for {semantic_call}")
                return cache_item.system_prompt_template, cache_item.user_prompt_template
        
        logger.info(f"No cached compilation found for {semantic_call}, compiling from scratch")
        compile_task_id = str(uuid.uuid4())
        compile_task_template = """
<compile_task task_id="{{compile_task_id}}">
    <call_context>
{{semantic_call.call_context}}
    </call_context>

    <location>
        <line_number>{{semantic_call.line_number_in_call_context}}</line_number>
        <method_name>{{semantic_call.method_name}}</method_name>
    </location>

    <parameter_spec>
        <positional>
{% for positional_parameter in semantic_call.positional_parameters %}
            <param position="{{positional_parameter[0]}}" type="{{positional_parameter[1]}}" />
{% endfor %}
        </positional>
        <keyword>
{% for keyword_parameter in semantic_call.keyword_parameters %}
            <param name="{{keyword_parameter.name}}" type="{{keyword_parameter}}" />
{% endfor %}
        </keyword>
    </parameter_spec>

    <return_specification>
        <type>{{semantic_call.return_type}}</type>
        <json_schema>
{{semantic_call.return_type.json_schema()}}
        </json_schema>
    </return_specification>
</compile_task>
"""
        compile_task = Template(compile_task_template).render(compile_task_id=compile_task_id, semantic_call=semantic_call)
        logger.debug(f"Compile task {compile_task_id} for {semantic_call}: {compile_task}")

        messages = [
            {"role": "system", "content": self._compile_prompt},
            {"role": "user", "content": compile_task}
        ]

        response = await acompletion(model=self._compile_model, messages=messages)
        response_content = response.choices[0].message.content.strip()
        logger.debug(f"Raw response content from compile LLM: {response_content}")
        
        if response_content.startswith("```"):
            response_content = response_content[len("```"):-len("```")].strip()
        
        system_prompt_start = f"=={compile_task_id}==SYSTEM_PROMPT=="
        system_prompt_end = f"=={compile_task_id}==END_SYSTEM_PROMPT=="
        user_prompt_start = f"=={compile_task_id}==USER_PROMPT=="
        user_prompt_end = f"=={compile_task_id}==END_USER_PROMPT=="

        system_prompt = response_content[response_content.find(system_prompt_start) + len(system_prompt_start):response_content.find(system_prompt_end)].strip()
        user_prompt = response_content[response_content.find(user_prompt_start) + len(user_prompt_start):response_content.find(user_prompt_end)].strip()

        logger.info(f"Successfully compiled {semantic_call} with task {compile_task_id}")
        self._save_compilation_cache(semantic_call, CacheItem(system_prompt, user_prompt))
        return system_prompt, user_prompt