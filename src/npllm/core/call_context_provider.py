import inspect
from abc import ABC, abstractmethod
from typing import List, Type, Set, Tuple
from dataclasses import dataclass

from npllm.core.semantic_call import SemanticCall
from npllm.utils.source_util import add_line_number
from npllm.utils.object_util import singleton

@dataclass
class CallContext:
    source: str
    semantic_call_line: int

class CallContextProvider(ABC):
    @abstractmethod
    def get_call_context(self, semantic_call: SemanticCall) -> CallContext:
        pass

@singleton
class FunctionCallContextProvider(CallContextProvider):
    def get_call_context(self, semantic_call: SemanticCall) -> CallContext:
        enclosing_function = semantic_call.enclosing_function
        if not enclosing_function:
            raise RuntimeError(f"Cannot find enclosing function at {semantic_call}")

        enclosing_function_source = semantic_call.enclosing_function_source

        return_type = semantic_call.return_type
        args_types = semantic_call.positional_parameters + semantic_call.keyword_parameters

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
            referenced_custom_types_sources.append((referenced_custom_type, semantic_call.get_class_source(referenced_custom_type)[0]))

        code_context = []
        absolute_line_number = semantic_call.line_number
        relative_line_number = absolute_line_number - enclosing_function.__code__.co_firstlineno + 1
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = relative_line_number + len(code_context)
        code_context.extend(enclosing_function_source.splitlines())
        return CodeContext(source=add_line_number(code_context), semantic_call_line=relative_line_number)

@singleton
class ClassCodeContextProvider(CodeContextProvider):
    def get_code_context(self, semantic_call: SemanticCall) -> CodeContext:
        enclosing_class = semantic_call.enclosing_class
        if not enclosing_class:
            raise RuntimeError(f"Cannot find enclosing class at {semantic_call}")

        _, first_line = inspect.getsourcelines(enclosing_class)
        enclosing_class_source = semantic_call.enclosing_class_source

        return_type = semantic_call.return_type
        args_types = semantic_call.positional_parameters + semantic_call.keyword_parameters

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
            referenced_custom_types_sources.append((referenced_custom_type, semantic_call.get_class_source(referenced_custom_type)[0]))

        code_context = []
        absolute_line_number = semantic_call.line_number
        relative_line_number = absolute_line_number - first_line + 1
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = relative_line_number + len(code_context)
        code_context.extend(enclosing_class_source.splitlines())

        return CodeContext(source=add_line_number(code_context), semantic_call_line=relative_line_number)

@singleton
class ModuleCodeContextProvider(CodeContextProvider):
    def get_code_context(self, semantic_call: SemanticCall) -> CodeContext:
        return_type = semantic_call.return_type
        args_types = semantic_call.positional_parameters + semantic_call.keyword_parameters

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
            class_source, class_module = semantic_call.get_class_source(referenced_custom_type)
            if class_module != semantic_call.enclosing_module:
                referenced_custom_types_sources.append((referenced_custom_type, class_source))

        code_context = []
        for _, referenced_custom_type_source in referenced_custom_types_sources[::-1]:
            code_context.extend(referenced_custom_type_source.splitlines())
            code_context.append("")
        
        relative_line_number = semantic_call.line_number + len(code_context)
        code_context.extend(semantic_call.enclosing_module_source.splitlines())
        return CodeContext(source=add_line_number(code_context), semantic_call_line=relative_line_number)