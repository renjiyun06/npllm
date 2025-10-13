import inspect
from abc import ABC, abstractmethod
from typing import List, Type, Set, Tuple
from dataclasses import dataclass

from npllm.core.call_site import CallSite
from npllm.utils.source_util import add_line_number
from npllm.utils.object_util import singleton

@dataclass
class CodeContext:
    source: str
    call_site_line: int

class CodeContextProvider(ABC):
    @abstractmethod
    def get_code_context(self, call_site: CallSite) -> CodeContext:
        pass

@singleton
class FunctionCodeContextProvider(CodeContextProvider):
    def get_code_context(self, call_site: CallSite) -> CodeContext:
        enclosing_function = call_site.enclosing_function
        if not enclosing_function:
            raise RuntimeError(f"Cannot find enclosing function at {call_site}")

        enclosing_function_source = call_site.enclosing_function_source

        return_type = call_site.return_type
        args_types = call_site.positional_parameters + call_site.keyword_parameters

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
            referenced_custom_types_sources.append((referenced_custom_type, call_site.get_class_source(referenced_custom_type)[0]))

        code_context = []
        absolute_line_number = call_site.line_number
        relative_line_number = absolute_line_number - enclosing_function.__code__.co_firstlineno + 1
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = relative_line_number + len(code_context)
        code_context.extend(enclosing_function_source.splitlines())
        return CodeContext(source=add_line_number(code_context), call_site_line=relative_line_number)

@singleton
class ClassCodeContextProvider(CodeContextProvider):
    def get_code_context(self, call_site: CallSite) -> CodeContext:
        enclosing_class = call_site.enclosing_class
        if not enclosing_class:
            raise RuntimeError(f"Cannot find enclosing class at {call_site}")

        _, first_line = inspect.getsourcelines(enclosing_class)
        enclosing_class_source = call_site.enclosing_class_source

        return_type = call_site.return_type
        args_types = call_site.positional_parameters + call_site.keyword_parameters

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
            referenced_custom_types_sources.append((referenced_custom_type, call_site.get_class_source(referenced_custom_type)[0]))

        code_context = []
        absolute_line_number = call_site.line_number
        relative_line_number = absolute_line_number - first_line + 1
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = relative_line_number + len(code_context)
        code_context.extend(enclosing_class_source.splitlines())

        return CodeContext(source=add_line_number(code_context), call_site_line=relative_line_number)

@singleton
class ModuleCodeContextProvider(CodeContextProvider):
    def get_code_context(self, call_site: CallSite) -> CodeContext:
        return_type = call_site.return_type
        args_types = call_site.positional_parameters + call_site.keyword_parameters

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
            class_source, class_module = call_site.get_class_source(referenced_custom_type)
            if class_module != call_site.enclosing_module:
                referenced_custom_types_sources.append((referenced_custom_type, class_source))

        code_context = []
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = call_site.line_number + len(code_context)
        code_context.extend(call_site.enclosing_module_source.splitlines())
        return CodeContext(source=add_line_number(code_context), call_site_line=relative_line_number)