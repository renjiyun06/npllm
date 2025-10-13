from typing import Any, List, Dict

from litellm import acompletion

from npllm.core.call_site import CallSite
from npllm.core.call_site_executor import CallSiteExecutor
from npllm.core.code_context_provider import CodeContextProvider, ModuleCodeContextProvider, FunctionCodeContextProvider
from npllm.core.llm_executor.compiler import Compiler
from npllm.core.llm_executor.compilers.default.default_compiler import DefaultCompiler
from npllm.utils.json_util import parse_json_str

import logging

logger = logging.getLogger(__name__)

class LLMExecutor(CallSiteExecutor):
    """LLMExecutor use the Compiler to translate the call site to prompts, and then invoke the runtime model to execute the call site"""
    def __init__(
        self, 
        runtime_model: str="openrouter/google/gemini-2.5-flash", 
        compiler: Compiler=DefaultCompiler("openrouter/google/gemini-2.5-pro")
    ):
        self._runtime_model = runtime_model
        self._compiler = compiler

    async def execute(self, call_site: CallSite, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        code_context_provider = self._code_context_provider
        if not call_site.enclosing_function and not call_site.enclosing_class:
            logger.info(f"Cannot find enclosing function or class at {call_site}, use module code context instead")
            code_context_provider = ModuleCodeContextProvider()

        # compile the call site to prompts
        compilation_result = await self._compiler.compile(call_site, code_context_provider)

        logger.info(f"Call runtime LLM with model {self._runtime_model} for {call_site}")
        system_prompt = compilation_result.system_prompt_template.format(
            args=args,
            kwargs=kwargs
        )
        logger.debug(f"Runtime LLM system prompt: {system_prompt}")

        user_prompt = None
        if compilation_result.user_prompt_template:
            user_prompt = compilation_result.user_prompt_template.format(
                args=args,
                kwargs=kwargs
            )
            logger.debug(f"Runtime LLM user prompt: {user_prompt}")

        messages = [{"role": "system", "content": system_prompt}]
        if user_prompt:
            messages.append({"role": "user", "content": user_prompt})
        
        # invoke the runtime model to execute the call site
        response = await acompletion(
            model=self._runtime_model,
            messages=messages,
            metadata={
                "run_name": "llm-executor-execute",
                "project_name": "npllm"
            }
        )

        response_content = response.choices[0].message.content.strip()
        logger.debug(f"Raw response content from runtime LLM: {response_content}")

        json_value = parse_json_str(response_content)

        value = call_site.return_type.pydantic_type_adapter().validate_python(json_value)
        logger.info(f"Successfully parsed the response from runtime LLM for {call_site}")
        return value