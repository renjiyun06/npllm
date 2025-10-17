import uuid
from typing import List, Any, Dict, Tuple
from dataclasses import dataclass

from litellm import acompletion

from npllm.core.ai import AI
from npllm.core.semantic_execute_engine import SemanticExecuteEngine
from npllm.core.semantic_call import SemanticCall
from npllm.core.execute_engines.bootstrap.bootstrap_execution_engine import BootstrapExecutionEngine
from npllm.utils.json_util import parse_json_str
from npllm.utils.template_placeholder_util import jinja2_placeholder_handler

import logging
logger = logging.getLogger(__name__)

@dataclass
class CompileTask:
    task_id: str
    call_context: str  # the call context of the semantic call
    line_number: int  # the line number of the semantic call in the call context
    method_name: str  # the method name of the semantic call
    positional_parameters: List[Tuple[int, str]]  # the positional parameters of the semantic call (index, type)
    keyword_parameters: List[Tuple[str, str]]  # the keyword parameters of the semantic call (name, type)
    return_type: str  # the return type of the semantic call
    json_schema: str  # the JSON schema of the return value of the semantic call 

class Compiler(AI):
    def __init__(self):
        AI.__init__(self, semantic_execute_engine=BootstrapExecutionEngine(
            compile_model="openrouter/google/gemini-2.5-pro",
            execution_model="openrouter/google/gemini-2.5-pro",
            template_placeholder_handler=jinja2_placeholder_handler
        ))

    async def compile(self, compile_task: CompileTask) -> Tuple[str, str]:
        """
        根据编译任务生成系统提示词模板和用户提示词模板

        @compile{
        该编译器的角色跟你一致, 因此你在当前流程中相当于一个元编译器.

        1. 该编译器必须知道关于 Semantic Python 的一切
        2. 该编译器在它为语义调用生成的提示词模版中必然需要引用语义调用的参数, 引用规范如下:
           - 使用 jinja2 模版语言引用参数
           - 位置参数引用: {{arg0}}, {{arg1}}
           - 关键字参数引用: {{user}}
           - 参数字段引用: {{arg0.field_name}}, {{user.name}}, {{user.address.city}}
        3. 该编译器同样需要支持 `@compile` 这个编译器指令

        以上是对该编译器的规定.

        以下是对你当前工作的指导:

        1. 首先你必须深刻理解你当前是一个元编译器
        2. 你当前需要处理的语义调用是: generate_system_prompt_and_user_prompt
        3. 该语义调用的返回值类型是: Tuple[str, str]
        4. **该编译器的返回值必须严格满足该类型, 即按照 <compile_task>.<return_specification>.<json_schema>, 注意, 此处是指你的 compile task**
        5. 由于你同样也需要在你生成的提示词模版中引用参数, 也就是 compile_task, 这里我规定你的引用形式如下:
           - 始终使用 arg0 代表 compile_task 这个参数, 因为它是一个位置参数.
           - 字段引用格式: {{arg0.field_name}}
           - 可以使用 jinja2 模版语言对一些字段值进行展开
        6. 如果你在给该编译器生成的提示词中使用了形如 `{{...}}` 的结构表述, 而该结构并不需要使用 jinja2 模版语言进行展开, 那么你必须将该结构放置在 raw 标签下, 如:
           {% raw %}{{...}}{% endraw %}
        """
        return await self.generate_system_prompt_and_user_prompt(compile_task)

class DefaultExecutionEngine(SemanticExecuteEngine):
    def __init__(self, execution_model: str="openrouter/google/gemini-2.5-flash"):
        self._compiler = Compiler()
        self._execution_model = execution_model
        self._template_placeholder_handler = jinja2_placeholder_handler

    async def execute(self, semantic_call: SemanticCall, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        task_id = str(uuid.uuid4())
        compile_task = CompileTask(
            task_id=task_id,
            call_context=semantic_call.call_context,
            line_number=semantic_call.line_number_in_call_context,
            method_name=semantic_call.method_name,
            positional_parameters=semantic_call.positional_parameters,
            keyword_parameters=semantic_call.keyword_parameters,
            return_type=semantic_call.return_type,
            json_schema=semantic_call.return_type.json_schema()
        )
        system_prompt_template, user_prompt_template = await self._compiler.compile(compile_task)
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