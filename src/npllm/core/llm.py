import inspect
import uuid
import logging
from typing import Any, Callable
from types import FrameType
import asyncio
import sys

from npllm.utils.notebook_util import is_in_notebook, last_cell_source
from npllm.utils.source_util import remove_indentation, add_line_number
from npllm.core.type import Type
from npllm.core.call_site import CallSite
from npllm.core.call_llm import LLMCallInfo, call_llm_async, call_llm_sync

logger = logging.getLogger(__name__)

class LLM:
    """
    The class makes the call of large language models as simple as calling local methods,
    and tightly integrates large language models with code so that they can understand the context of the code.

    Example:

    llm = LLM(role="You are a helpful assistant")
    response = await llm.summarize(text="...")

    Or it can be used as a base class to define a more specific LLM with a specific role:
    
    class CodeAssistant(LLM):
        \"\"\"You are a coding assistant, you help the user to write code\"\"\"
        def __init__(self):
            LLM().__init__(self)

        async def write_code(self, requirement: str) -> str:
            code = await self.reason(requirement=requirement) # here is the magic happens
            return code
        ...

    There is no prompt at all, all the context is from the code itself, including the comments.
    """
    def __init__(self, role=None, model="openrouter/google/gemini-2.5-flash", **kwargs):
        self.role: str = role
        if not self.role and self.__class__.__name__ != "LLM":
            self.role = self.__class__.__doc__ or ""
        self.role = self.role.strip() if self.role and self.role.strip() else "You are a helpful assistant"
        self.model: str = model
        self._llm_kwargs = kwargs

    def _get_caller_frame_outside_llm(self) -> FrameType:
        # get the caller frame outside the LLM class
        caller_frame = inspect.currentframe()
        while caller_frame:
            if caller_frame.f_code.co_filename != __file__:
                return caller_frame
            caller_frame = caller_frame.f_back
        raise RuntimeError("Cannot find caller frame outside LLM class")

    def __getattr__(self, method_name: str) -> Callable:
        async def llm_method_handler_async(*args, **kwargs) -> Any:
            call_id = str(uuid.uuid4())
            logger.info(f"LLM method {method_name} called with call id {call_id}")

            caller_frame: FrameType = self._get_caller_frame_outside_llm()
            absolute_call_line_number = caller_frame.f_lineno
            source = None
            if is_in_notebook(caller_frame) and caller_frame.f_code.co_name == "<module>":
                # the caller frame is in a notebook, and not a function, then we get the source code from the last cell
                # it's not the recommended way to use npllm in a notebook, better to wrap the code in a function
                source = last_cell_source()
                relative_call_line_number = caller_frame.f_lineno
            else:
                source = remove_indentation(inspect.getsource(caller_frame.f_code))
                relative_call_line_number = caller_frame.f_lineno - caller_frame.f_code.co_firstlineno + 1

            if not source:
                raise RuntimeError("Cannot get source code of the caller")
            
            call_site: CallSite = CallSite.call_site(caller_frame, source, relative_call_line_number, absolute_call_line_number, method_name, sync=False)
            expected_return_type: Type = call_site.get_return_type()

            # assemble the code context
            # code context includes:
            # 1. the source code of all related dataclass, including the dataclass of the arguments and the return type
            # 2. the type alias
            # 3. the source code of the caller function
            dataclass_source_lines = []
            for dataclass_source in call_site.related_dataclass_sources(args, kwargs).values():
                dataclass_source_lines.extend(dataclass_source.splitlines())
                dataclass_source_lines.append("")

            type_alias_sources = []
            for type_alias_source in expected_return_type.type_alias_sources().values():
                type_alias_sources.append(type_alias_source)
                type_alias_sources.append("")

            source_lines = source.splitlines()

            call_line_number = relative_call_line_number + len(dataclass_source_lines) + len(type_alias_sources)
            code_context = dataclass_source_lines + type_alias_sources + source_lines

            llm_call_info = LLMCallInfo(
                call_id=call_id,
                role=self.role,
                method_name=method_name,
                args=args,
                kwargs=kwargs,
                expected_return_type=expected_return_type,
                code_context=add_line_number(code_context),
                call_line_number=call_line_number,
                model=self.model,
                llm_kwargs=self._llm_kwargs,
            )
            return await call_llm_async(llm_call_info)
        
        def llm_method_handler_sync(*args, **kwargs) -> Any:
            call_id = str(uuid.uuid4())
            logger.info(f"LLM method {method_name} called with call id {call_id}")

            caller_frame: FrameType = self._get_caller_frame_outside_llm()
            absolute_call_line_number = caller_frame.f_lineno
            source = None
            if is_in_notebook(caller_frame) and caller_frame.f_code.co_name == "<module>":
                # the caller frame is in a notebook, and not a function, then we get the source code from the last cell
                # it's not the recommended way to use npllm in a notebook, better to wrap the code in a function
                source = last_cell_source()
                relative_call_line_number = caller_frame.f_lineno
            elif caller_frame.f_code.co_name == "<module>":
                # the caller frame is in a script, and not a function, then we just get the current line
                module_name = caller_frame.f_globals.get('__name__')
                module = sys.modules[module_name]
                module_source = inspect.getsource(module)
                relative_call_line_number = 1
                source = remove_indentation("\n".join(module_source.splitlines()[absolute_call_line_number - 1: absolute_call_line_number]))
            else:
                source = remove_indentation(inspect.getsource(caller_frame.f_code))
                relative_call_line_number = caller_frame.f_lineno - caller_frame.f_code.co_firstlineno + 1
            
            if not source:
                raise RuntimeError("Cannot get source code of the caller")
            
            call_site: CallSite = CallSite.call_site(caller_frame, source, relative_call_line_number, absolute_call_line_number, method_name, sync=True)
            expected_return_type: Type = call_site.get_return_type()

            # assemble the code context
            # code context includes:
            # 1. the source code of all related dataclass, including the dataclass of the arguments and the return type
            # 2. the type alias
            # 3. the source code of the caller function
            dataclass_source_lines = []
            for dataclass_source in call_site.related_dataclass_sources(args, kwargs).values():
                dataclass_source_lines.extend(dataclass_source.splitlines())
                dataclass_source_lines.append("")

            type_alias_sources = []
            for type_alias_source in expected_return_type.type_alias_sources().values():
                type_alias_sources.append(type_alias_source)
                type_alias_sources.append("")

            source_lines = source.splitlines()

            call_line_number = relative_call_line_number + len(dataclass_source_lines) + len(type_alias_sources)
            code_context = dataclass_source_lines + type_alias_sources + source_lines

            llm_call_info = LLMCallInfo(
                call_id=call_id,
                role=self.role,
                method_name=method_name,
                args=args,
                kwargs=kwargs,
                expected_return_type=expected_return_type,
                code_context=add_line_number(code_context),
                call_line_number=call_line_number,
                model=self.model,
                llm_kwargs=self._llm_kwargs,
            )
            return call_llm_sync(llm_call_info)
        
        class DualCallable:
            def __init__(self, async_func, sync_func):
                self.async_func = async_func
                self.sync_func = sync_func

            def __call__(self, *args, **kwargs):
                try:
                    asyncio.get_running_loop()
                    return self.async_func(*args, **kwargs)
                except RuntimeError:
                    return self.sync_func(*args, **kwargs)
            
            def __await__(self):
                return self.async_func().__await__()
            
        return DualCallable(llm_method_handler_async, llm_method_handler_sync)
