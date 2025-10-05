from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Any, Dict

from npllm.core.call_site import CallSite
from npllm.core.code_context import CodeContext

class SystemPromptTemplate(ABC):
    @abstractmethod
    def format(self, output_json_schema: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
        pass

class UserPromptTemplate(ABC):
    @abstractmethod
    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        pass

@dataclass
class CompilationResult:
    system_prompt_template: SystemPromptTemplate
    user_prompt_template: Optional[UserPromptTemplate]

class Compiler(ABC):
    @abstractmethod
    async def compile(self, call_site: CallSite, code_context: CodeContext) -> CompilationResult:
        pass