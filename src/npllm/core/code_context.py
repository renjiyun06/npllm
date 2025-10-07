import inspect
from abc import ABC, abstractmethod
from typing import Tuple, List, Type, Set

from npllm.core.call_site import CallSite
from npllm.core.runtime_context import RuntimeContext
from npllm.utils.source_util import add_line_number

class CodeContext(ABC):
    @abstractmethod
    def get_code_context(self, call_site: CallSite, runtime_context: RuntimeContext) -> Tuple[str, int]:
        pass

class FunctionCodeContext(CodeContext):
    def get_code_context(self, call_site: CallSite, runtime_context: RuntimeContext) -> Tuple[str, int]:
        enclosing_function = call_site.enclosing_function
        if not enclosing_function:
            raise RuntimeError(f"Cannot find enclosing function at call site {call_site}")

        enclosing_function_source = runtime_context.get_function_source(enclosing_function)

        return_type = call_site.return_type
        args_types = call_site.args_types

        referenced_custom_types = []
        referenced_custom_types.extend(return_type.get_referenced_custom_classes())
        for _, arg_type in args_types:
            referenced_custom_types.extend(arg_type.get_referenced_custom_classes())

        visited: Set[Type] = set()
        referenced_custom_types_sources: List[Tuple[Type, str]] = []
        for referenced_custom_type in referenced_custom_types:
            if referenced_custom_type in visited:
                continue
            visited.add(referenced_custom_type)
            referenced_custom_types_sources.append((referenced_custom_type, runtime_context.get_class_source(referenced_custom_type)))

        code_context = []
        absolute_line_number = call_site.identifier.line_number
        relative_line_number = absolute_line_number - enclosing_function.__code__.co_firstlineno + 1
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = relative_line_number + len(code_context)
        code_context.extend(enclosing_function_source.splitlines())
        return add_line_number(code_context), relative_line_number


class ClassCodeContext(CodeContext):
    def get_code_context(self, call_site: CallSite, runtime_context: RuntimeContext) -> Tuple[str, int]:
        enclosing_class = call_site.enclosing_class
        if not enclosing_class:
            raise RuntimeError(f"Cannot find enclosing class at call site {call_site}")

        _, first_line = inspect.getsourcelines(enclosing_class)
        enclosing_class_source = runtime_context.get_class_source(enclosing_class)

        return_type = call_site.return_type
        args_types = call_site.args_types

        referenced_custom_types = []
        referenced_custom_types.extend(return_type.get_referenced_custom_classes())
        for _, arg_type in args_types:
            referenced_custom_types.extend(arg_type.get_referenced_custom_classes())

        visited: Set[Type] = set()
        referenced_custom_types_sources: List[Tuple[Type, str]] = []
        for referenced_custom_type in referenced_custom_types:
            if referenced_custom_type in visited:
                continue
            visited.add(referenced_custom_type)
            referenced_custom_types_sources.append((referenced_custom_type, runtime_context.get_class_source(referenced_custom_type)))

        code_context = []
        absolute_line_number = call_site.identifier.line_number
        relative_line_number = absolute_line_number - first_line + 1
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = relative_line_number + len(code_context)
        code_context.extend(enclosing_class_source.splitlines())

        return add_line_number(code_context), relative_line_number

class ModuleCodeContext(CodeContext):
    def get_code_context(self, call_site: CallSite, runtime_context: RuntimeContext) -> Tuple[str, int]:
        module_source = call_site.get_module_source(call_site.enclosing_module)
        return add_line_number(module_source.splitlines()), call_site.identifier.line_number