from typing import List, Any, Dict

from npllm.core.ai import AI
from npllm.core.llm_executor.compiler import Compiler, CompilationResult
from npllm.core.llm_executor.compiler import PromptTemplate
from npllm.core.call_site import CallSite
from npllm.core.llm_executor.llm_executor import LLMExecutor
from npllm.core.llm_executor.compilers.meta.meta_compiler import MetaCompiler

class SystemPromptTemplate(PromptTemplate):
    def __init__(self):
        pass

    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        pass

class UserPromptTemplate(PromptTemplate):
    def __init__(self):
        pass
    
    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        pass

class DefaultCompiler(Compiler, AI):
    def __init__(self):
        AI.__init__(
            self,
            call_site_executor=LLMExecutor(
                runtime_model="openrouter/google/gemini-2.5-flash",
                compiler=MetaCompiler(model="openrouter/google/gemini-2.5-pro")
            )
        )

    def compile(self, call_site: CallSite) -> CompilationResult:
        pass