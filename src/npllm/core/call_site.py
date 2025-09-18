from abc import ABC, abstractmethod
import ast
import typing
from types import FrameType
from typing import Dict
import inspect
from dataclasses import is_dataclass

from npllm.core.type import Type, BasicType, AnyType, TupleType
from npllm.utils.notebook_util import is_in_notebook, cell_source

class CallSite(ABC):
    """
    The call site of a method at a specific line of code
    """
    @classmethod
    def call_site(cls, frame: FrameType, source: str, relative_call_line_number: int, absolute_call_line_number: int, method_name: str) -> 'CallSite':
        tree = ast.parse(source)
        if not is_in_notebook(frame):
            module_filename = inspect.getmodule(frame).__file__
        else:
            module_filename = "<notebook>"

        for node in ast.walk(tree):
            if hasattr(node, 'lineno') and node.lineno == relative_call_line_number:
                if isinstance(node, ast.If) and isinstance(node.test, ast.Await) and node.test.value.func.attr == method_name:
                    return IfCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                elif isinstance(node, ast.While) and isinstance(node.test, ast.Await) and node.test.value.func.attr == method_name:
                    return WhileCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                    return AssignCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                    return AnnAssignCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                elif isinstance(node, ast.Call) and node.func.attr == method_name:
                    # here means that there is indeed a call to the method on the current line of code,
                    # but the call is not in an if expression, assignment statement, or assignment statement with type annotation
                    raise RuntimeError(f"Call site for method {method_name} at line {absolute_call_line_number} in {module_filename} is not supported yet")

        raise RuntimeError(f"Cannot find call site for method {method_name} at line {absolute_call_line_number} in {module_filename}")
    
    def __init__(
            self, 
            frame: FrameType, 
            tree: ast.AST, 
            caller_node: ast.AST, 
            source: str, 
            module_filename: str,
            relative_call_line_number: int, 
            absolute_call_line_number: int,
            method_name: str):
        """At relative_call_line_number of the source code, the method with method_name is called by the caller_node in the AST tree"""
        # the frame of the caller
        self._frame = frame
        self._tree = tree
        self._caller_node: ast.AST = caller_node
        self._source = source
        # if the caller is in a module file, then it's the filename of the module file
        # if the caller is in a notebook, then it's "<notebook>"
        self._module_filename = module_filename
        # the line number of the call in the source code, starting from 1
        self._relative_call_line_number = relative_call_line_number
        # the absolute line number of the call in the module file, starting from 1
        self._absolute_call_line_number = absolute_call_line_number
        self._method_name = method_name
        self._module_file_tree: ast.AST = None

        if not is_in_notebook(self._frame):
            module_file_source = inspect.getsource(inspect.getmodule(self._frame))
            self._module_file_tree = ast.parse(module_file_source)

        self._return_type: Type = self._parse_return_type()

    @abstractmethod
    def _parse_return_type(self) -> Type:
        pass

    def get_return_type(self) -> Type:
        return self._return_type

    def get_dataclass(self, class_name, parent_class) -> typing.Type:
        """
        Get the class object by its name in the caller's frame.
        If the class can be find in the globals of the caller's frame, return it.
        Otherwise try to find it in the parent_class's module if parent_class is not None.
        """
        if class_name in self._frame.f_globals:
            return self._frame.f_globals[class_name]
        
        if not parent_class or not is_dataclass(parent_class):
            return None
        
        parent_class_module = parent_class.__module__
        module = __import__(parent_class_module)
        dataclass_cls = getattr(module, class_name, None)
        if dataclass_cls is None or not is_dataclass(dataclass_cls):
            return None
        return dataclass_cls

    def is_in_notebook(self) -> bool:
        return is_in_notebook(self._frame)

    def related_dataclass_sources(self, args, kwargs) -> Dict[str, str]:
        """
        Get the source code of all related dataclass, including the dataclass of the arguments and the return type
        """
        result = {}
        result.update(self._return_type.related_dataclass_sources())
        for arg in args:
            # here we just check if the argument is a dataclass or a list of dataclass,
            # any other complex data structure is not considered for now
            if hasattr(arg, '__dataclass_fields__'):
                result[arg.__class__.__qualname__] = inspect.getsource(arg.__class__)
            elif isinstance(arg, list) and len(arg) > 0 and hasattr(arg[0], '__dataclass_fields__'):
                result[arg[0].__class__.__qualname__] = inspect.getsource(arg[0].__class__)

        for _, v in kwargs.items():
            if hasattr(v, '__dataclass_fields__'):
                result[v.__class__.__qualname__] = inspect.getsource(v.__class__)

        return result

class IfCallSite(CallSite):
    """
    The caller node is an ast.If node

    Example:
    if await llm.reason(...):
        ...
    """
    def _parse_return_type(self) -> Type:
        return BasicType("bool")

class WhileCallSite(CallSite):
    """
    The caller node is an ast.While node

    Example:
    while await llm.reason(...):
        ...
    """
    def _parse_return_type(self) -> Type:
        return BasicType("bool")

class AssignCallSite(CallSite):
    """
    The caller node is an ast.Assign node

    Example:
    x = await llm.reason(...)
    (x, y) = await llm.reason(...)
    x.y = await llm.reason(...)
    """
    def _parse_return_type(self) -> Type:
        target = self._caller_node.targets[0]
        if isinstance(target, ast.Tuple):
            elts_len = len(target.elts)
            item_types = [AnyType() for _ in range(elts_len)]
            # let large language model to infer the type of each item in the tuple from the code context
            return TupleType(item_types=tuple(item_types))
        
        # we need to find the declaration of the target variable in the code context
        if is_in_notebook(self._frame):
            var_name = target.id
        elif isinstance(target, ast.Attribute):
            var_name = target.value.id + '.' + target.attr
        else:
            var_name = target.id

        declaration_node = self._find_declaration_node(var_name)

        if not declaration_node:
            # we cannot find the declaration of the target variable, return AnyType
            return AnyType()
        
        annotation = declaration_node.annotation
        type = Type.from_annotation(annotation, self)
        if type:
            return type

        raise RuntimeError(f"Cannot parse return type at line {self._absolute_call_line_number} for method {self._method_name} in {self._module_filename}")

    def _find_declaration_node(self, var_name: str) -> ast.AnnAssign:
        declaration_node = None
        if is_in_notebook(self._frame):
            # we find the declaration in the previous cells if we are in a notebook
            i = -1
            source = cell_source(i)
            found = False
            while source is not None and not found:
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, ast.AnnAssign) and node.target.id == var_name:
                        declaration_node = node
                        found = True
                        break
                i -= 1
                source = cell_source(i)
        else:
            # we find the declaration in the current module file
            for node in ast.walk(self._module_file_tree):
                if isinstance(node, ast.AnnAssign):
                    if isinstance(node.target, ast.Attribute):
                        if node.target.value.id + '.' + node.target.attr == var_name:
                            declaration_node = node
                            break
                    elif node.target.id == var_name:
                            declaration_node = node
                            break
        
        return declaration_node


class AnnAssignCallSite(CallSite):
    """
    The caller node is an ast.AnnAssign node

    Example:
    x: int = await llm.reason(...)
    """
    def _parse_return_type(self) -> Type:
        caller_node: ast.AnnAssign = self._caller_node
        annotation = caller_node.annotation
        type = Type.from_annotation(annotation, self)
        if type:
            return type

        raise RuntimeError(f"Cannot parse return type at line {self._absolute_call_line_number} for method {self._method_name} in {self._module_filename}")