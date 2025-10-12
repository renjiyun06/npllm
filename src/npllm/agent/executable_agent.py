from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass

from pydantic import TypeAdapter

@dataclass
class Task:
    title: str
    description: str
    output_json_schema: str

class ExecutableAgent(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    @abstractmethod
    def introduce_yourself(self) -> str:
        pass

    @abstractmethod
    async def execute(self, task: Task, output_type_adapter: TypeAdapter) -> Any:
        pass