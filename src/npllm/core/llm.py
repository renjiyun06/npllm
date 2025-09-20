import inspect
import uuid
import logging
from typing import Any, Callable
from types import FrameType

from npllm.utils.notebook_util import is_in_notebook, last_cell_source
from npllm.utils.source_util import remove_indentation, add_line_number
from npllm.core.type import Type
from npllm.core.call_site import CallSite
from npllm.core.call_llm import LLMCallInfo, call_llm

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
    def __init__(self, role=None, model="openrouter/google/gemini-2.5-flash"):
        self.role: str = role
        if not self.role and self.__class__.__name__ != "LLM":
            self.role = self.__class__.__doc__ or ""
        self.model: str = model

    def __getattr__(self, method_name: str) -> Callable:
        async def llm_method_handler(*args, **kwargs) -> Any:
            call_id = str(uuid.uuid4())
            logger.info(f"LLM method {method_name} called with call id {call_id}")

            # get the caller frame who called this method
            caller_frame: FrameType = inspect.currentframe().f_back
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
            
            call_site: CallSite = CallSite.call_site(caller_frame, source, relative_call_line_number, absolute_call_line_number, method_name)
            expected_return_type: Type = call_site.get_return_type()

            # assemble the code context
            # code context includes:
            # 1. the source code of all related dataclass, including the dataclass of the arguments and the return type
            # 2. the type alias
            # 3. role as a comment of the caller function
            # 4. the source code of the caller function
            dataclass_source_lines = []
            for dataclass_source in call_site.related_dataclass_sources(args, kwargs).values():
                dataclass_source_lines.extend(dataclass_source.splitlines())
                dataclass_source_lines.append("")

            type_alias_sources = []
            for type_alias_source in expected_return_type.type_alias_sources().values():
                type_alias_sources.append(type_alias_source)
                type_alias_sources.append("")

            role_comment_lines = []
            if self.role and self.role.strip():
                # populate the role template with the instance variables
                role = self.role.strip().format(**self.__dict__)
                role_comment_lines = f"""\"\"\"\n{role}\n\"\"\"""".splitlines()

            source_lines = source.splitlines()

            call_line_number = relative_call_line_number + len(dataclass_source_lines) + len(type_alias_sources) + len(role_comment_lines)
            code_context = dataclass_source_lines + type_alias_sources + role_comment_lines + source_lines

            llm_call_info = LLMCallInfo(
                call_id=call_id,
                method_name=method_name,
                args=args,
                kwargs=kwargs,
                expected_return_type=expected_return_type,
                code_context=add_line_number(code_context),
                call_line_number=call_line_number,
                model=self.model
            )
            return await call_llm(llm_call_info)

        return llm_method_handler
