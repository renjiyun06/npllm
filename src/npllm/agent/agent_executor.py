from typing import Any, List, Dict, Tuple

from npllm.core.ai import AI
from npllm.core.call_site import CallSite
from npllm.core.call_site_executor import CallSiteExecutor
from npllm.core.code_context_provider import ModuleCodeContextProvider, ClassCodeContextProvider, FunctionCodeContextProvider
from npllm.agent.executable_agent import ExecutableAgent, Task
from npllm.core.llm_executor.llm_executor import LLMExecutor

import logging

logger = logging.getLogger(__name__)

class DefaultExecutableAgent(AI, ExecutableAgent):
    def __init__(self):
        AI.__init__(self, LLMExecutor(code_context_provider=ClassCodeContextProvider()))
        ExecutableAgent.__init__(self, "default_executable_agent")
    
    def introduce_yourself(self) -> str:
        return "A helpful assistant"
    
    async def execute(self, task: Task) -> Any:
        return await self.execute_task(task)

class AgentExecutor(AI, CallSiteExecutor):
    def __init__(self):
        AI.__init__(self, LLMExecutor())
        CallSiteExecutor.__init__(self)
        self._agent_registry: Dict[str, ExecutableAgent] = {}
        self.register_agent(DefaultExecutableAgent())

    def register_agent(self, agent: ExecutableAgent):
        if agent.agent_id in self._agent_registry:
            logger.warning(f"Agent {agent.agent_id} already registered")
        self._agent_registry[agent.agent_id] = agent

    async def execute(self, call_site: CallSite, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        code_context_provider = None
        if call_site.enclosing_function:
            code_context_provider = FunctionCodeContextProvider()
        elif call_site.enclosing_class:
            code_context_provider = ClassCodeContextProvider()
        else:
            code_context_provider = ModuleCodeContextProvider()

        code_context = code_context_provider.get_code_context(call_site)
        
        source: str = code_context.source
        call_site_line: int = code_context.call_site_line
        call_site_method: str = call_site.method_name

        # Generate a task's title and description.
        # The task will be executed by another agent, so the task's description MUST:
        # - Be clear, actionable, and specific, using domain-specific language
        # - Seamlessly integrate actual args/kwargs values into the description naturally
        #   - WRONG: "According to the instruction 'randomly generate', ..."
        #   - CORRECT: "Randomly generate..."
        task_title, task_description = await self.generate_task(source, call_site_line, call_site_method, args, kwargs, return_type=Tuple[str, str])

        agents: Dict[str, str] = {agent_id: agent.introduce_yourself() for agent_id, agent in self._agent_registry.items()}
        target_agent_id = None
        if len(agents) == 1:
            target_agent_id = list(agents.keys())[0]
        else:
            target_agent_id = await self.select_most_suitable_agent(task_title, task_description, agents)
        
        task = Task(
            title=task_title,
            description=task_description,
            output_json_schema=call_site.return_type.json_schema()
        )
        task_result = await self._agent_registry[target_agent_id].execute(task)
        return call_site.return_type.pydantic_type_adapter().validate_python(task_result)