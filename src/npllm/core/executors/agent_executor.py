from abc import ABC, abstractmethod
from typing import Any, List, Dict
from dataclasses import dataclass

from npllm.core.ai import AI
from npllm.core.call_site import CallSite
from npllm.core.call_site_executor import CallSiteExecutor
from npllm.core.code_context_provider import ModuleCodeContextProvider

import logging

logger = logging.getLogger(__name__)

@dataclass
class Task:
    title: str
    description: str

@dataclass
class OutputSpec:
    json_schema: str
    format_guidance: str

class ExecutableAgent(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    @abstractmethod
    def introduce_yourself(self) -> str:
        pass

    @abstractmethod
    async def execute(self, task: Task, output_spec: OutputSpec) -> Any:
        pass

class DefaultAgent(AI, ExecutableAgent):
    def __init__(self):
        AI.__init__(self)
        ExecutableAgent.__init__(self, "default")
        
    async def execute(self, task: Task, output_spec: OutputSpec) -> Any:
        return await self.execute_task(task, output_spec)

    def introduce_yourself(self) -> str:
        return "A helpful assistant"

class AgentExecutor(AI, CallSiteExecutor):
    def __init__(self):
        AI.__init__(self)
        CallSiteExecutor.__init__(self)
        self._agent_registry: Dict[str, ExecutableAgent] = {}
        self.register_agent(DefaultAgent())

    def register_agent(self, agent: ExecutableAgent):
        if agent.agent_id in self._agent_registry:
            logger.warning(f"Agent {agent.agent_id} already registered")
        self._agent_registry[agent.agent_id] = agent

    async def execute(self, call_site: CallSite, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        code_context_provider = ModuleCodeContextProvider()
        code_context = code_context_provider.get_code_context(call_site)
        
        source: str = code_context.source
        call_site_line: int = code_context.call_site_line
        call_site_method: str = call_site.method_name
        # Generate a concrete task instance for the call_site_method at call_site_line in source.
        # Requirements:
        # - Seamlessly integrate actual args/kwargs values into the task description naturally
        # - WRONG: "According to the instruction 'randomly generate', ..."
        # - CORRECT: "Randomly generate..."
        # - Use domain language
        # - The task will be executed by other agent, so write as clear, actionable instructions
        task: Task = await self.generate_task(source, call_site_line, call_site_method, args, kwargs)

        agents: Dict[str, str] = {agent_id: agent.introduce_yourself() for agent_id, agent in self._agent_registry.items()}
        target_agent_id: str = await self.select_most_suitable_agent(task, agents)
        output_spec = OutputSpec(
            json_schema=call_site.return_type.json_schema(),
            format_guidance=""
        )
        return await self._agent_registry[target_agent_id].execute(task, output_spec)