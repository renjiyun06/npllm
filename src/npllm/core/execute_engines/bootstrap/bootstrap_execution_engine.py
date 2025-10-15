import uuid
import re
from importlib import resources

from litellm import acompletion

from npllm.core.semantic_execute_engine import SemanticExecuteEngine
from npllm.core.semantic_call import SemanticCall
from typing import List, Any, Dict, Tuple

from npllm.utils.json_util import parse_json_str

import logging

logger = logging.getLogger(__name__)

class CacheItem:
    def __init__(self, system_prompt_template: str, user_prompt_template: str):
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template

    def check_valid(self, semantic_call: SemanticCall) -> bool:
        pass

class BootstrapExecutionEngine(SemanticExecuteEngine):
    def __init__(
        self,
        compile_model: str="openrouter/google/gemini-2.5-flash",
        execution_model: str="openrouter/google/gemini-2.5-flash", 
    ):
        self._compile_model = compile_model
        self._execution_model = execution_model
        self._compile_prompt = None
        with resources.open_text("npllm.core.execute_engines.bootstrap", "compile_prompt.md") as f:
            self._compile_prompt = f.read()

        self._compilation_cache: Dict[SemanticCall, CacheItem] = {}
        self._load_compilation_cache()

    def _load_compilation_cache(self):
        pass

    def _save_compilation_cache(self, semantic_call: SemanticCall, cache_item: CacheItem):
        pass

    def _format_template(self, template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
        placeholders = re.findall(r"{{[^}]+}}", template)
        for original_placeholder in placeholders:
            placeholder = original_placeholder
            placeholder = placeholder.replace("{{", "").replace("}}", "")
            
            root_obj = None
            dot_chain = []
            if placeholder.startswith("arg"):
                placeholder = placeholder[len("arg"):]
                position_index = int(placeholder.split(".")[0])
                root_obj = args[position_index]
                dot_chain = placeholder.split(".")[1:]
            else:
                root_obj = kwargs[placeholder.split(".")[0]]
                dot_chain = placeholder.split(".")[1:]

            value = root_obj
            for field in dot_chain:
                value = getattr(value, field)

            formatted_value: List[str] = []
            if isinstance(value, list):
                for item in value:
                    formatted_value.append(str(item))
            else:
                formatted_value.append(str(value))

            template = template.replace(original_placeholder, "\n".join(formatted_value))

        return template.strip()

    async def execute(self, semantic_call: SemanticCall, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        system_prompt_template, user_prompt_template = await self._compile(semantic_call)

        system_prompt = self._format_template(system_prompt_template, args, kwargs)
        user_prompt = self._format_template(user_prompt_template, args, kwargs)
        
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
        positional_parameters = []
        keyword_parameters = []
        for arg_name, arg_type in semantic_call.positional_parameters + semantic_call.keyword_parameters:
            if isinstance(arg_name, int):
                positional_parameters.append(f"""<param position="{arg_name}" type="{arg_type}" />""")
            else:
                keyword_parameters.append(f"""<param name="{arg_name}" type="{arg_type}" />""")

        compile_task = f"""
<compile_task task_id="{compile_task_id}">
    <call_context>
{semantic_call.call_context}
    </call_context>

    <location>
        <line_number>{semantic_call.line_number_in_call_context}</line_number>
        <method_name>{semantic_call.method_name}</method_name>
    </location>

    <parameter_spec>
        <positional>
{'\n'.join(positional_parameters)}
        </positional>
        <keyword>
{'\n'.join(keyword_parameters)}
        </keyword>
    </parameter_spec>

    <return_specification>
        <type>{semantic_call.return_type}</type>
        <json_schema>
{semantic_call.return_type.json_schema()}
        </json_schema>
    </return_specification>
</compile_task>
""".strip()

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
        notes_start = f"=={compile_task_id}==NOTES=="
        notes_end = f"=={compile_task_id}==END_NOTES=="

        system_prompt = response_content[response_content.find(system_prompt_start) + len(system_prompt_start):response_content.find(system_prompt_end)].strip()
        user_prompt = response_content[response_content.find(user_prompt_start) + len(user_prompt_start):response_content.find(user_prompt_end)].strip()
        notes = response_content[response_content.find(notes_start) + len(notes_start):response_content.find(notes_end)].strip()

        logger.info(f"Successfully compiled {semantic_call} with task {compile_task_id}")
        logger.debug(f"System prompt generated for {semantic_call} with task {compile_task_id}: {system_prompt}")
        logger.debug(f"User prompt generated for {semantic_call} with task {compile_task_id}: {user_prompt}")
        logger.debug(f"Compilation notes for {semantic_call} with task {compile_task_id}: {notes}")
        self._save_compilation_cache(semantic_call, CacheItem(system_prompt, user_prompt))
        return system_prompt, user_prompt