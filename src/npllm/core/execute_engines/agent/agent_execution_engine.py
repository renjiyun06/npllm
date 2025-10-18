from typing import List, Any, Dict, Tuple
from dataclasses import dataclass

from npllm.core.ai import AI
from npllm.core.annotated_type import AnnotatedType
from npllm.core.semantic_call import SemanticCall as SC
from npllm.core.execute_engines.bootstrap.bootstrap_execution_engine import BootstrapExecutionEngine
from npllm.core.execute_engines.default.default_execution_engine import DefaultExecutionEngine
from npllm.core.meta_template import tempate_a_placeholder_handler, tempate_b_placeholder_handler

import logging 

logger = logging.getLogger(__name__)

@dataclass
class Task:
    title: str
    description: str

@dataclass
class SemanticCall:
    call_context: str  # the call context of the semantic call
    line_number: int  # the line number of the semantic call in the call context
    method_name: str  # the method name of the semantic call
    positional_parameters: List[Tuple[int, str]]  # the positional parameters of the semantic call (index, type)
    keyword_parameters: List[Tuple[str, str]]  # the keyword parameters of the semantic call (name, type)

class TaskGenerator(AI):
    def __init__(self):
        AI.__init__(self, semantic_execute_engine=BootstrapExecutionEngine(
            compile_model="openrouter/google/gemini-2.5-pro",
            execution_model="openrouter/google/gemini-2.5-flash",
            template_placeholder_handler=tempate_a_placeholder_handler
        ))

    async def generate_task(self, semantic_call: SemanticCall) -> Task:
        """
        @compile{
        TaskGenerator 的角色跟你自己的角色非常类似, 你的任务是将 semantic call 转译成提示词模版, 之后该提示词模版将会交给 execution llm 执行.
        而对于 TaskGenerator 来讲, 它的任务是将 semantic call 翻译成一个任务, 而该任务将提交给一个通用代理执行.
        
        对 TaskGenerator 的具体规定:
        1. TaskGenerator 虽然也是做 semantic call 的转译, 但是它**无需知道**任何关于 Semantic Python 的信息
        2. TaskGenerator 在为 semantic call 生成任务描述时, 必然需要引用 semantic call 的参数, 引用规范如下:
           - 使用 Template-B 模版语言来引用参数
           - 引用位置参数: <%= arg0 %>, <%= arg1 %>
           - 引用关键字参数, 直接使用参数名引用, 如 <%= user %>
           - 引用参数字段, 使用 dot notation 引用, 如 <%= arg0.name %>, <%= user.address.city %>
        3. 生成的任务描述必须在 Template-B 模版语言的配合下, 结构优秀, 可读性高, 且是通过领域自然语言书写的
        
        对你当前工作的指导:
        1. 首先你需要理解 TaskGenerator 这个角色和你之间的类似和不同点
        2. 你当前正在处理的语义调用是: do_generate_task. 此处需要注意以下几点:
           - 你正在编译该语义调用, 但是你并不执行该语义调用, 执行该语义调用的是 TaskGenerator, 因此你需要给出符合它角色的提示词
           - 该语义调用的返回值类型是 `Task`, 它所对应 JSON Schema 已在给你的 compile_task 中指定
           - 因此你必须明确跟 TaskGenerator 交代清楚, 它的返回值必须严格匹配该类型. **注意与你自己的输出进行区分, 切勿混淆**
        3. 由于你同样也需要在你生成的提示词模版中引用参数, 也就是 semantic_call, 这里我规定你的引用形式如下:
           - 使用 Template-A 模版语言来引用参数
           - 始终使用 <<arg0>> 来引用 semantic_call, 因为它是一个位置参数
           - 可以采用 Template-A 的相关语法来展开一些字段值
        4. **你必须教会 TaskGenerator 如何正确地使用 Template-B 来进行参数引用, 告知其语法并配上相关示例**
        5. Template-A 和 Template-B 这两种模版语言只支持变量替换和循环展开, 切勿使用其他你自己设想的语法, 同时你也必须将这点告知 TaskGenerator
        6. 输出提示词时, 配合模版语言, 尽可能做到最后的输出是美观的, 具备完美的可读性, 同时你也需要将这点告知 TaskGenerator, 使其生成的任务描述清晰易读.
        
        Template-A:
        使用 `<<variable>>` 输出变量, `<:loop collection as item:>...<:/loop:>` 进行循环, 示例:
        Hello <<name>>!
        <:loop users as user:>
        - <<user.name>> (<<user.age>>)
            <:loop user.tags as tag:>
            #<<tag>>
            <:/loop:>
        <:/loop:>

        Template-B:
        使用 `<%= variable %>` 输出变量, `<% .each do |...| %>...<% end %>` 进行循环. 示例:
        Hello <%= name %>!
        <% users.each do |user| %>
        - <%= user.name %> (<%= user.age %>)
            <% user.tags.each do |tag| %>
            #<%= tag %>
            <% end %>
        <% end %>
        }@
        """
        return await self.do_generate_task(semantic_call)

class Assistant(AI):
    def __init__(self):
        AI.__init__(self, semantic_execute_engine=DefaultExecutionEngine())

    async def do_task(self, task: Task, expected_return_type: AnnotatedType) -> Any:
        return_type_json_schema: str = expected_return_type.json_schema()

        # 该返回值必须是一个满足 return_type_json_schema 的 JSON 字符串, 且一定要单行返回, 切勿做任何的美观格式化操作.
        # @compile 由于使用的 execution llm 在逻辑上比较差, 你应该给出几个示例, 如何才是遵循了 JSON Schema
        result: Any = await self.execute_task(task, return_type_json_schema)
        return expected_return_type.pydantic_type_adapter().validate_python(result)

class AgentExecutionEngine:
    def __init__(self):
        self._task_generator = TaskGenerator()
        self._agent = Assistant()
        self._template_placeholder_handler = tempate_b_placeholder_handler

    async def execute(self, sc: SC, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        semantic_call = SemanticCall(
            call_context=sc.call_context,
            line_number=sc.line_number_in_call_context,
            method_name=sc.method_name,
            positional_parameters=sc.positional_parameters,
            keyword_parameters=sc.keyword_parameters
        )

        task = await self._task_generator.generate_task(semantic_call)
        task.description = self._template_placeholder_handler(task.description, args, kwargs)
        return await self._agent.do_task(task, sc.return_type)