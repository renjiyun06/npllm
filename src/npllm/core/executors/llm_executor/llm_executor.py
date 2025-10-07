import json
from typing import Any, List, Dict

from litellm import acompletion
import json_repair

from npllm.core.call_site import CallSite
from npllm.core.call_site_executor import CallSiteExecutor
from npllm.core.code_context import CodeContext, ModuleCodeContext, FunctionCodeContext
from npllm.core.executors.llm_executor.compiler import Compiler
from npllm.core.executors.llm_executor.compilers.default.default_compiler import DefaultCompiler

import logging

logger = logging.getLogger(__name__)


class LLMExecutor(CallSiteExecutor):
    def __init__(
        self, 
        runtime_model: str="openrouter/google/gemini-2.5-flash", 
        code_context: CodeContext=FunctionCodeContext(),
        compiler: Compiler=DefaultCompiler("openrouter/google/gemini-2.5-pro")
    ):
        self._runtime_model = runtime_model
        self._code_context = code_context
        self._compiler = compiler

    async def execute(self, call_site: CallSite, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        code_context = self._code_context
        if not call_site.enclosing_function and not call_site.enclosing_class:
            logger.info(f"Cannot find enclosing function or class at call site {call_site}, use module code context instead")
            code_context = ModuleCodeContext()

        compilation_result = await self._compiler.compile(call_site, code_context)

        logger.info(f"Call runtime LLM with model {self._runtime_model} for call site {call_site}")
        system_prompt = compilation_result.system_prompt_template.format(args=args, kwargs=kwargs)
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
        
        response = await acompletion(
            model=self._runtime_model,
            messages=messages
        )

        response_content = response.choices[0].message.content.strip()
        logger.debug(f"Raw response content from runtime LLM: {response_content}")

        if response_content.startswith("```json"):
            response_content = response_content[len("```json"):-len("```")].strip()

        json_value = None
        if (
            response_content.startswith("{") and response_content.endswith("}") or 
            response_content.startswith("[") and response_content.endswith("]") or
            response_content in ["true", "false", "null"] or
            response_content.isdigit()
        ):
            json_value = json_repair.loads(response_content)
        elif response_content.startswith('"') and response_content.endswith('"'):
            try:
                json_value = json.loads(response_content)
            except Exception as e:
                # it means the response content is a json string, but not correctly escaped
                # just let the whole string as the json value
                json_value = response_content
        else:
            json_value = response_content

        value = call_site.return_type.pydantic_type_adapter().validate_python(json_value)
        logger.info(f"Successfully parsed the response from runtime LLM for call site {call_site}")
        return value