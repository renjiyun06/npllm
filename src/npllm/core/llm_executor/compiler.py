from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Any, Dict

from npllm.core.call_site import CallSite
from npllm.core.code_context_provider import CodeContextProvider
from npllm.core.code_context_provider import FunctionCodeContextProvider
from npllm.core.code_context_provider import ClassCodeContextProvider
from npllm.core.code_context_provider import ModuleCodeContextProvider

class PromptTemplate(ABC):
    @abstractmethod
    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        pass

@dataclass
class CompilationResult:
    system_prompt_template: PromptTemplate
    user_prompt_template: Optional[PromptTemplate]

class Compiler(ABC):
    @abstractmethod
    async def compile(self, call_site: CallSite) -> CompilationResult:
        pass

    def code_context_provider(self, call_site: CallSite) -> CodeContextProvider:
        if call_site.enclosing_function:
            return FunctionCodeContextProvider()
        elif call_site.enclosing_class:
            return ClassCodeContextProvider()
        else:
            return ModuleCodeContextProvider()