from typing import List, Any, Dict

from litellm import acompletion

from npllm.core.llm_executor.compiler import Compiler, CompilationResult
from npllm.core.llm_executor.compiler import PromptTemplate
from npllm.core.call_site import CallSite

import logging

logger = logging.getLogger(__name__)

class SystemPromptTemplate(PromptTemplate):
    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        pass

class UserPromptTemplate(PromptTemplate):
    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        pass

class MetaCompiler(Compiler):
    def __init__(self, model: str):
        self._model = model

    def compile(self, call_site: CallSite) -> CompilationResult:
        pass