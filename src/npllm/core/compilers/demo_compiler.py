from dataclasses import dataclass
from typing import List, Any, Dict, Tuple

from pydantic import BaseModel, Field

from npllm.core.llm import LLM
from npllm.core.compiler import Compiler, CompilationResult, SystemPromptTemplate as spt, UserPromptTemplate as upt
from npllm.core.call_site import CallSite as cs
from npllm.core.code_context import CodeContext as cc

import logging

logger = logging.getLogger(__name__)

class DemoCompilationResult(BaseModel):
    system_prompt: str = Field(description="The system prompt for the runtime LLM")
    user_prompt_template: str = Field(description="The user prompt template for the runtime LLM")

@dataclass
class CallSite:
    line_number: int
    method_name: str
    positional_parameters: List[Tuple[int, str]]
    keyword_parameters: List[Tuple[str, str]]
    expected_return_type: str

@dataclass
class CodeContext:
    code_snippets_with_line_numbers: str

class SystemPromptTemplate(spt):
    def __init__(self, system_prompt: str):
        self._system_prompt = system_prompt
    
    def format(self, output_json_schema: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
        return self._system_prompt

class UserPromptTemplate(upt):
    def __init__(self, user_prompt_template: str):
        self._user_prompt_template = user_prompt_template
    
    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        return self._user_prompt_template

class DemoCompiler(Compiler):
    def __init__(self):
        self._llm = LLM()

    async def compile(self, call_site: cs, code_context: cc) -> CompilationResult:
        code_snippets_with_line_numbers, line_number = code_context.get_code_context(call_site, call_site)
        
        result = await self._do_compile(
            CallSite(
                line_number=line_number,
                method_name=call_site.identifier.method_name,
                positional_parameters=call_site.positional_parameters,
                keyword_parameters=call_site.keyword_parameters,
                expected_return_type=str(call_site.return_type)
            ),
            CodeContext(
                code_snippets_with_line_numbers=code_snippets_with_line_numbers
            )
        )
        return CompilationResult(
            system_prompt_template=SystemPromptTemplate(result.system_prompt),
            user_prompt_template=UserPromptTemplate(result.user_prompt_template)
        )

    async def _do_compile(self, call_site: CallSite, code_context: CodeContext) -> DemoCompilationResult:
        # @compile{
        # This is also a compile-time LLM, it is responsible for the same role as you, 
        # so you need to impart your points on completing the task to it
        # }@
        return await self._llm.reason(call_site, code_context)