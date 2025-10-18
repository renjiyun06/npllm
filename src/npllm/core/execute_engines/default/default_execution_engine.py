import uuid
from importlib import resources
from typing import List, Any, Dict, Tuple
from dataclasses import dataclass

from litellm import acompletion

from npllm.core.ai import AI
from npllm.core.semantic_execute_engine import SemanticExecuteEngine
from npllm.core.semantic_call import SemanticCall
from npllm.core.execute_engines.bootstrap.bootstrap_execution_engine import BootstrapExecutionEngine
from npllm.utils.json_util import parse_json_str
from npllm.core.meta_template import tempate_a_placeholder_handler, tempate_b_placeholder_handler

from npllm.utils.module_util import module_hash

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
    def __init__(self, execution_model: str="openrouter/google/gemini-2.5-pro"):
        AI.__init__(self, semantic_execute_engine=BootstrapExecutionEngine(
            compile_model="openrouter/google/gemini-2.5-pro",
            execution_model=execution_model,
            template_placeholder_handler=tempate_b_placeholder_handler
        ))

    async def compile(self, compile_task: CompileTask) -> Tuple[str, str]:
        """
        @compile{
        该编译器的角色跟你的一致, 因此在当前流程中, 你相当于一个元编译器.
        
        对该编译器的具体规定:
        1. 该编译器必须知道关于 Semantic Python 的一切
        2. 该编译器在它为语义调用生成的提示词模版中必然需要引用语义调用的参数, 引用规范如下:
           - 使用 Template-A 模版语言来引用参数
           - 引用位置参数: <%= arg0 %>, <%= arg1 %>
           - 引用关键字参数, 直接使用参数名引用, 如 <%= user %>
           - 引用参数字段, 使用 dot notation 引用, 如 <%= arg0.name %>, <%= user.address.city %>
        3. 该编译器同样需要支持 `@compile` 这个编译器指令
        
        对你当前工作的指导:
        1. 首先你必须深刻理解你当前是一个元编译器
        2. 你当前需要处理的语义调用是: generate_system_prompt_and_user_prompt
        3. 该语义调用的返回值类型是: Tuple[str, str]
        4. 该编译器的返回值必须严格满足该类型, 即按照 <compile_task>.<return_specification>.<json_schema>, 注意, 此处是指你的 compile task
        5. 由于你同样也需要在你生成的提示词模版中引用参数, 也就是 compile_task, 这里我规定你的引用形式如下:
           - 使用 Template-B 模版语言来引用参数
           - 始终使用 <<arg0>> 来引用 compile_task, 因为它是一个位置参数
           - 可以采用 Template-B 的相关语法来展开一些字段值
        6. 你必须教会该编译器如何正确地使用 Template-A 来进行参数引用, 告知其语法并配上相关示例.
        
        Template-A:
        使用 `<%= variable %>` 输出变量, `<% .each do |...| %>...<% end %>` 进行循环. 示例:
        Hello <%= name %>!
        <% users.each do |user| %>
        - <%= user.name %> (<%= user.age %>)
            <% user.tags.each do |tag| %>
            #<%= tag %>
            <% end %>
        <% end %>
        
        Template-B:
        使用 `<<variable>>` 输出变量, `<:loop collection as item:>...<:/loop:>` 进行循环, 示例:
        Hello <<name>>!
        <:loop users as user:>
        - <<user.name>> (<<user.age>>)
            <:loop user.tags as tag:>
            #<<tag>>
            <:/loop:>
        <:/loop:>
        }@
        """
        return await self.generate_system_prompt_and_user_prompt(compile_task)

@dataclass
class CacheItem:
    system_prompt_template: str
    user_prompt_template: str
    dependent_modules: Dict[str, str]

    def check_valid(self, semantic_call: SemanticCall) -> bool:
        current_dependent_modules = semantic_call.dependent_modules
        if len(current_dependent_modules) != len(self.dependent_modules):
            return False
        
        for module_filename, dependent_module in current_dependent_modules.items():
            if module_filename not in self.dependent_modules:
                return False
            if module_hash(dependent_module) != self.dependent_modules[module_filename]:
                return False
        return True

class DefaultExecutionEngine(SemanticExecuteEngine):
    def __init__(
        self, 
        compile_model: str="openrouter/google/gemini-2.5-flash", 
        execution_model: str="openrouter/google/gemini-2.5-flash"
    ):
        self._compiler = Compiler(execution_model=compile_model)
        self._execution_model = execution_model
        self._template_placeholder_handler = tempate_a_placeholder_handler
        
        self._compilation_cache: Dict[str, CacheItem] = {}
        self._load_compilation_cache()

    def _load_compilation_cache(self):
        for file in resources.files("npllm.generated.default_execution_engine").iterdir():
            if file.is_file() and file.name.endswith(".txt"):
                compile_task_id = file.name.replace(".txt", "")
                with open(file, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    semantic_call_start = f"=={compile_task_id}==SEMANTIC_CALL=="
                    semantic_call_end = f"=={compile_task_id}==END_SEMANTIC_CALL=="
                    semantic_call = content[content.find(semantic_call_start) + len(semantic_call_start):content.find(semantic_call_end)].strip()
                    
                    system_prompt_start = f"=={compile_task_id}==SYSTEM_PROMPT==" 
                    system_prompt_start_index = content.find(system_prompt_start)
                    system_prompt_end = f"=={compile_task_id}==END_SYSTEM_PROMPT=="
                    system_prompt_end_index = content.find(system_prompt_end)
                    system_prompt = content[system_prompt_start_index:system_prompt_end_index].strip()

                    user_prompt_start = f"=={compile_task_id}==USER_PROMPT=="
                    user_prompt_start_index = content.find(user_prompt_start)
                    user_prompt_end = f"=={compile_task_id}==END_USER_PROMPT=="
                    user_prompt_end_index = content.find(user_prompt_end)
                    user_prompt = content[user_prompt_start_index:user_prompt_end_index].strip()

                    dependent_modules = {}
                    for module_and_hash in content[user_prompt_end_index+len(user_prompt_end):].split("\n"):
                        if module_and_hash.strip():
                            module_filename, module_hash = module_and_hash.split(":")
                            dependent_modules[module_filename] = module_hash
                    
                    self._compilation_cache[semantic_call] = CacheItem(system_prompt, user_prompt, dependent_modules)

    def _save_compilation_cache(self, semantic_call: SemanticCall, cache_item: CacheItem, compile_task_id: str):
        self._compilation_cache[str(semantic_call)] = cache_item
        with resources.path("npllm.generated.default_execution_engine", f"{compile_task_id}.txt") as cache_file_path:
            with open(cache_file_path, "w", encoding="utf-8") as f:
                f.write(f"=={compile_task_id}==SEMANTIC_CALL==\n{semantic_call}\n=={compile_task_id}==END_SEMANTIC_CALL==\n")
                f.write(f"=={compile_task_id}==SYSTEM_PROMPT==\n{cache_item.system_prompt_template}\n=={compile_task_id}==END_SYSTEM_PROMPT==\n")   
                f.write(f"=={compile_task_id}==USER_PROMPT==\n{cache_item.user_prompt_template}\n=={compile_task_id}==END_USER_PROMPT==\n")
                for module_filename, module_hash in cache_item.dependent_modules.items():
                    f.write(f"{module_filename}:{module_hash}\n")

    async def execute(self, semantic_call: SemanticCall, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        system_prompt_template = None
        user_prompt_template = None
        if str(semantic_call) in self._compilation_cache:
            cache_item = self._compilation_cache[str(semantic_call)]
            if cache_item.check_valid(semantic_call):
                logger.info(f"Using cached compilation for {semantic_call}")
                system_prompt_template = cache_item.system_prompt_template
                user_prompt_template = cache_item.user_prompt_template

        if system_prompt_template is None or user_prompt_template is None:
            logger.info(f"No cached compilation found for {semantic_call}, compiling from scratch")
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
            self._save_compilation_cache(semantic_call, CacheItem(system_prompt_template, user_prompt_template, {module_filename: module_hash(module) for module_filename, module in semantic_call.dependent_modules.items()}), task_id)

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