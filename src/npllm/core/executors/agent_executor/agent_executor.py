from abc import ABC, abstractmethod
from typing import Any, List, Dict
from dataclasses import dataclass

from npllm.core.ai import AI
from npllm.core.call_site import CallSite
from npllm.core.call_site_executor import CallSiteExecutor
from npllm.core.code_context_provider import CodeContextProvider, ModuleCodeContextProvider

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

class DefaultAgent(ExecutableAgent):
    def __init__(self):
        super().__init__("default")
        self._ai = AI()
        
    async def execute(self, task: Task, output_spec: OutputSpec) -> Any:
        return await self._ai.execute(task, output_spec)

    def introduce_yourself(self) -> str:
        return "I am a helpful assistant"

class AgentExecutor(CallSiteExecutor):
    def __init__(self):
        self._ai = AI()
        self._agents: Dict[str, ExecutableAgent] = {"default": DefaultAgent()}

    def register_agent(self, agent: ExecutableAgent):
        self._agents[agent.agent_id] = agent

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
        task: Task = await self._ai.generate_task(source, call_site_line, call_site_method, args, kwargs)
        output_spec = OutputSpec(
            json_schema=call_site.return_type.json_schema(),
            format_guidance=""
        )
        return await self._agents["default"].execute(task, output_spec)