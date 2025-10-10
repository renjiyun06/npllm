import json
from typing import Any, List, Dict

import litellm
from litellm import acompletion
import json_repair

from npllm.core.call_site import CallSite
from npllm.core.call_site_executor import CallSiteExecutor
from npllm.core.code_context_provider import CodeContextProvider, ModuleCodeContextProvider, FunctionCodeContextProvider
from npllm.core.executors.llm_executor.compiler import Compiler
from npllm.core.executors.llm_executor.compilers.default.default_compiler import DefaultCompiler

import logging

logger = logging.getLogger(__name__)

litellm.callbacks = ["langsmith"]

class LLMExecutor(CallSiteExecutor):
    def __init__(
        self, 
        runtime_model: str="openrouter/google/gemini-2.5-flash", 
        code_context_provider: CodeContextProvider=FunctionCodeContextProvider(),
        compiler: Compiler=DefaultCompiler("openrouter/google/gemini-2.5-pro")
    ):
        self._runtime_model = runtime_model
        self._code_context_provider = code_context_provider
        self._compiler = compiler

    def _extract_json_str(self, response_content: str) -> str:
        json_str = response_content
        if json_str.startswith("```json"):
            json_str = json_str[len("```json"):-len("```")].strip()
        elif json_str.startswith("```"):
            json_str = json_str[len("```"):-len("```")].strip()
        elif json_str.startswith("`"):
            json_str = json_str[len("`"):-len("`")].strip()
        
        return json_str

    async def execute(self, call_site: CallSite, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        code_context_provider = self._code_context_provider
        if not call_site.enclosing_function and not call_site.enclosing_class:
            logger.info(f"Cannot find enclosing function or class at {call_site}, use module code context instead")
            code_context_provider = ModuleCodeContextProvider()

        compilation_result = await self._compiler.compile(call_site, code_context_provider)

        logger.info(f"Call runtime LLM with model {self._runtime_model} for {call_site}")
        system_prompt = compilation_result.system_prompt_template.format(
            output_json_schema=call_site.return_type.json_schema(),
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

        json_str = self._extract_json_str(response_content)
        json_value = None
        if (
            json_str.startswith("{") and json_str.endswith("}") or 
            json_str.startswith("[") and json_str.endswith("]") or
            json_str in ["true", "false", "null"] or
            json_str.isdigit()
        ):
            json_value = json_repair.loads(json_str)
        elif json_str.startswith('"') and json_str.endswith('"'):
            try:
                json_value = json.loads(json_str)
            except Exception as e:
                # it means the response content is a json string, but not correctly escaped
                # just let the whole string as the json value
                json_value = json_str
        else:
            json_value = json_str

        value = call_site.return_type.pydantic_type_adapter().validate_python(json_value)
        logger.info(f"Successfully parsed the response from runtime LLM for {call_site}")
        return value