import inspect
import uuid
import asyncio
import os
from types import FrameType
from typing import Any, Callable, Optional
from litellm import acompletion
import json

import json_repair

from npllm.core.compiler import Compiler
from npllm.core.call_site import CallSite
from npllm.core.code_context import CodeContext, FunctionCodeContext, ModuleCodeContext
from npllm.core.compilers.default.default_compiler import DefaultCompiler

import logging

logger = logging.getLogger(__name__)

class LLM:
    def __init__(
        self, 
        model: str="openrouter/google/gemini-2.5-flash",
        compiler: Optional[Compiler] = None,
        code_context: Optional[CodeContext] = None
    ):
        self._runtime_model = model
        self._compiler = compiler or DefaultCompiler("openrouter/google/gemini-2.5-pro")
        self._code_context = code_context or FunctionCodeContext()

    def __getattr__(self, method_name: str) -> Callable:

        def generate_call_id() -> str:
            return str(uuid.uuid4())

        def caller_frame() -> FrameType:
            caller_frame = inspect.currentframe()
            asyncio_path = os.path.dirname(asyncio.__file__)
            while caller_frame:
                if caller_frame.f_code.co_filename != __file__ and asyncio_path not in caller_frame.f_code.co_filename:
                    return caller_frame
                caller_frame = caller_frame.f_back
            raise RuntimeError("Cannot find caller frame outside LLM class")
        
        async def llm_method_handler(*args, **kwargs) -> Any:
            call_id = generate_call_id()
            logger.info(f"LLM call {method_name} with call id {call_id}")
            call_site = CallSite.of(caller_frame(), method_name, kwargs['__is_async__'])
            
            code_context = self._code_context
            if not call_site.enclosing_function and not call_site.enclosing_class:
                logger.info(f"Cannot find enclosing function or class at call site {call_site}, use module code context instead")
                code_context = ModuleCodeContext()

            compilation_result = await self._compiler.compile(call_site, code_context)

            logger.info(f"Call runtime LLM with model {self._runtime_model} for call site {call_site}")
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
        
        def llm_method_handler_sync(*args, **kwargs) -> Any:
            return asyncio.run(llm_method_handler(*args, **kwargs))
            
        class DualCallable:
            def __init__(self, async_func, sync_func):
                self.async_func = async_func
                self.sync_func = sync_func

            def __call__(self, *args, **kwargs):
                if asyncio._get_running_loop():
                    kwargs['__is_async__'] = True
                    return self.async_func(*args, **kwargs)
                else:
                    kwargs['__is_async__'] = False
                    return self.sync_func(*args, **kwargs)

        return DualCallable(llm_method_handler, llm_method_handler_sync)