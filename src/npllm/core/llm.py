import inspect
import uuid
import logging
from typing import Any, Callable, Type, Dict, Optional, Tuple
from types import FrameType
import asyncio
import sys

from npllm.utils.notebook_util import is_in_notebook, last_cell_source
from npllm.utils.source_util import remove_indentation, add_line_number
from npllm.core.type import Type
from npllm.core.call_site import CallSite
from npllm.core.call_llm import LLMCallInfo, LLMCallResult, call_llm_async, call_llm_sync

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

    _next_program_snippet_id = 0
    # all the funcs that have been inspected
    _inspected_funcs: Dict[Type, Dict[Callable, Tuple[str, str]]] = {}

    @classmethod
    def self_inspect(cls, agent_cls: Type) -> Callable:
        """
        This decorator is used to enable the agent to inspect the whole system's code,
        especially self inspect the code it is in, so that it can understand the context and intent of the code better
        """
        def _self_inspect(func: Callable) -> Callable:
            if agent_cls not in cls._inspected_funcs:
                cls._inspected_funcs[agent_cls] = {}
            
            program_snippet_id = f"PSI-{cls._next_program_snippet_id:04d}"
            cls._next_program_snippet_id += 1
            # extract the source code of the func
            source = remove_indentation(inspect.getsource(func))
            cls._inspected_funcs[agent_cls][func] = (program_snippet_id, source)
            return func

        return _self_inspect

    def __init__(self, role=None, model="openrouter/google/gemini-2.5-flash", **kwargs):
        self.role: str = role
        if not self.role and self.__class__.__name__ != "LLM":
            self.role = self.__class__.__doc__ or ""
        self.role = self.role.strip() if self.role and self.role.strip() else "You are a helpful assistant"
        self.model: str = model
        self._llm_kwargs = kwargs

        self._inspected_mode: bool = False
        self._inspected_funcs: Dict[Callable, (str, str)] = {}
        self._program_snippets: str = None

        self._self_inspect()

        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._total_completion_cost = 0.0

    def _self_inspect(self):
        """
        Give the agent a chance to inspect the code it is in or other critical system code
        """
        inspected_funcs = LLM._inspected_funcs.get(self.__class__, {})
        if not inspected_funcs:
            return
        
        self._inspected_mode = True
        self._inspected_funcs = LLM._inspected_funcs[self.__class__]
        
        # beautify the program snippets
        program_snippets = []
        for program_snippet_id, source in self._inspected_funcs.values():
            program_snippets.append(f"{program_snippet_id}:")
            program_snippets.append("```python")
            program_snippets.extend(source.splitlines())
            program_snippets.append("```")
            program_snippets.append("")

        # remove the last empty line
        program_snippets = program_snippets[:-1]
        self._program_snippets = "\n".join(program_snippets)

    def _get_caller_frame_outside_llm(self) -> FrameType:
        # get the caller frame outside the LLM class
        caller_frame = inspect.currentframe()
        while caller_frame:
            # only the outside frame or __init__ frame is valid
            if caller_frame.f_code.co_filename != __file__ or caller_frame.f_code.co_name == "_self_inspect":
                return caller_frame
            caller_frame = caller_frame.f_back
        raise RuntimeError("Cannot find caller frame outside LLM class")
    
    def _get_caller_function(self, caller_frame: FrameType) -> Optional[Callable]:
        func_name = caller_frame.f_code.co_name
        caller_func = None
        if "self" in caller_frame.f_locals:
            # the caller is a method of a class
            self_obj = caller_frame.f_locals["self"]
            bound_method = getattr(self_obj, func_name, None)
            if bound_method:
                caller_func = bound_method.__func__
        else:
            # the caller is a function
            module_name = caller_frame.f_globals.get('__name__')
            module = sys.modules[module_name]
            caller_func = getattr(module, func_name, None)
        
        return caller_func
    
    def _get_current_program_snippet_id(self, caller_frame: FrameType) -> Optional[str]:
        """
        Get the current program snippet's id which the llm method is called in
        """
        caller_func = self._get_caller_function(caller_frame)
        if not caller_func:
            return None
        
        if caller_func in self._inspected_funcs:
            return self._inspected_funcs[caller_func][0]
        
        return None

    def __getattr__(self, method_name: str) -> Callable:
        async def llm_method_handler_async(*args, **kwargs) -> Any:
            call_id = str(uuid.uuid4())
            logger.info(f"LLM method {method_name} called with call id {call_id}")

            caller_frame: FrameType = self._get_caller_frame_outside_llm()

            current_program_snippet_id = self._get_current_program_snippet_id(caller_frame)
            if self._inspected_mode and not current_program_snippet_id:
                raise RuntimeError("LLM method must be called in a function/method inspected by itself")

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
                program_snippets=self._program_snippets,
                current_program_snippet_id=current_program_snippet_id,
                llm_kwargs=self._llm_kwargs,
                inspected_mode=self._inspected_mode,
            )
            llm_call_result = await call_llm_async(llm_call_info)
            logger.info(f"LLM call {llm_call_result.call_id} used {llm_call_result.prompt_tokens} input tokens, {llm_call_result.completion_tokens} output tokens, cost ${llm_call_result.completion_cost:.6f}")
            self._total_input_tokens += llm_call_result.prompt_tokens
            self._total_output_tokens += llm_call_result.completion_tokens
            self._total_completion_cost += llm_call_result.completion_cost
            return llm_call_result.result
        
        def llm_method_handler_sync(*args, **kwargs) -> Any:
            call_id = str(uuid.uuid4())
            logger.info(f"LLM method {method_name} called with call id {call_id}")

            caller_frame: FrameType = self._get_caller_frame_outside_llm()

            current_program_snippet_id = self._get_current_program_snippet_id(caller_frame)
            if self._inspected_mode and not current_program_snippet_id:
                raise RuntimeError("LLM method must be called in a function/method inspected by itself")

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
                # we need the extract the current line and the comments just before it by checking the indentation
                current_line = module_source.splitlines()[absolute_call_line_number - 1]
                indentation = len(current_line) - len(current_line.lstrip())
                i = absolute_call_line_number - 2
                while i >= 0:
                    line = module_source.splitlines()[i]
                    if line.strip() == "":
                        # empty line, continue
                        i -= 1
                        continue
                    current_indentation = len(line) - len(line.lstrip())
                    if current_indentation == indentation and line.lstrip().startswith("#"):
                        i -= 1
                        continue
                    break
                relative_call_line_number = absolute_call_line_number - i - 1
                source = remove_indentation("\n".join(module_source.splitlines()[i + 1: absolute_call_line_number]))
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
                program_snippets=self._program_snippets,
                current_program_snippet_id=current_program_snippet_id,
                llm_kwargs=self._llm_kwargs,
                inspected_mode=self._inspected_mode,
            )
            llm_call_result = call_llm_sync(llm_call_info)
            logger.info(f"LLM call {llm_call_result.call_id} used {llm_call_result.prompt_tokens} input tokens, {llm_call_result.completion_tokens} output tokens, cost ${llm_call_result.completion_cost:.6f}")
            self._total_input_tokens += llm_call_result.prompt_tokens
            self._total_output_tokens += llm_call_result.completion_tokens
            self._total_completion_cost += llm_call_result.completion_cost
            return llm_call_result.result
        
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
