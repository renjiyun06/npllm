from abc import ABC, abstractmethod
import ast
import typing
from types import FrameType
from typing import List, Optional, Callable
import inspect
from dataclasses import is_dataclass
import logging

from npllm.core.type import Type, BoolType, AnyType, TupleType
from npllm.utils.notebook_util import is_in_notebook, cell_source, get_dataclass_source

logger = logging.getLogger(__name__)

class CallSite(ABC):
    """
    The call site of a method at a specific line of code
    """
    @classmethod
    def call_site(
        cls, 
        frame: FrameType, 
        source: str, 
        relative_call_line_number: int, 
        absolute_call_line_number: int, 
        method_name: str,
        sync: bool = False
    ) -> 'CallSite':
        tree = ast.parse(source)
        if not is_in_notebook(frame):
            module_filename = inspect.getmodule(frame).__file__
        else:
            module_filename = "<notebook>"

        for node in ast.walk(tree):
            if hasattr(node, 'lineno') and node.lineno == relative_call_line_number:
                if not sync:
                    if isinstance(node, ast.If) and isinstance(node.test, ast.Await) and node.test.value.func.attr == method_name:
                        return IfCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.While) and isinstance(node.test, ast.Await) and node.test.value.func.attr == method_name:
                        return WhileCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                        return AssignCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                        return AnnAssignCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.Return) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                        return ReturnCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.Call) and node.func.attr == method_name:
                        # here means that there is indeed a call to the method on the current line of code,
                        # but the call is not in an if expression, assignment statement, or assignment statement with type annotation
                        raise RuntimeError(f"Call site for method {method_name} at line {absolute_call_line_number} in {module_filename} is not supported yet")
                else:
                    if isinstance(node, ast.If) and isinstance(node.test, ast.Call) and node.test.func.attr == method_name:
                        return IfCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.While) and isinstance(node.test, ast.Call) and node.test.func.attr == method_name:
                        return WhileCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and node.value.func.attr == method_name:
                        return AssignCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call) and node.value.func.attr == method_name:
                        return AnnAssignCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
                    elif isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and node.value.func.attr == method_name:
                        return ReturnCallSite(frame, tree, node, source, module_filename, relative_call_line_number, absolute_call_line_number, method_name)
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
        self._module = inspect.getmodule(frame)
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

    def get_module_file_tree(self) -> Optional[ast.AST]:
        return self._module_file_tree

    def get_return_type(self) -> Type:
        return self._return_type

    def get_dataclass(self, class_name, parent_class) -> Optional[typing.Type]:
        """
        Get the class by its name in the caller's frame

        If the class can be find in the globals of the caller's frame, return it.
        Otherwise try to find it in the parent_class's module if parent_class is not None, for example:

        module a.py:
        @dataclass
        class A:
            x: int
            y: str
        
        module b.py:
        from a import A
        @dataclass
        class B:
            a: A

        Here if we want to find class A in the call site of module b.py, we can find it in the module of class B
        """
        if class_name in self._frame.f_globals:
            dataclass_cls = self._frame.f_globals[class_name]
            if is_dataclass(dataclass_cls):
                return dataclass_cls
            else:
                return None
        
        if not parent_class or not is_dataclass(parent_class):
            return None
        
        parent_class_module = parent_class.__module__
        module = __import__(parent_class_module)
        dataclass_cls = getattr(module, class_name, None)
        if dataclass_cls and is_dataclass(dataclass_cls):
            return dataclass_cls

        return None
    
    def get_dataclass_source(self, dataclass_cls) -> Optional[str]:
        """
        Get the source code of the dataclass

        Here we need to handle two cases:
        1. the dataclass have source file, we can get the source code by inspect.getsource
        2. the dataclass is defined in a notebook, we need to get the source code from the notebook cells
        """
        if not dataclass_cls or not is_dataclass(dataclass_cls):
            return None
        
        try:
            source = inspect.getsource(dataclass_cls)
            return source
        except Exception as e:
            logger.debug(f"Cannot get source of dataclass {dataclass_cls.__qualname__} by inspect.getsource: {e}")
            if self.is_in_notebook():
                return get_dataclass_source(dataclass_cls)
        
        return None
    
    def get_module(self):
        return self._module

    def is_in_notebook(self) -> bool:
        return is_in_notebook(self._frame)

    def related_sources(self, args, kwargs) -> List[str]:
        """
        Get the source code of all related dataclass, including the dataclass of the arguments and the return type
        """

        result = []

        dataclass_sources = {}
        dataclass_sources.update(self._return_type.related_dataclass_sources())

        for source in dataclass_sources.values():
            if source not in result:
                result.append(source)

        alias_sources = self._return_type.type_alias_sources()
        for source in alias_sources.values():
            if source not in result:
                result.append(source)

        for arg in args:
            # here we just check if the argument is a dataclass or a list of dataclass,
            # any other complex data structure is not considered for now
            if is_dataclass(arg) and not isinstance(arg, type) and arg.__class__.__qualname__ not in dataclass_sources:
                result.append(inspect.getsource(arg.__class__))
            elif isinstance(arg, list) and len(arg) > 0 and is_dataclass(arg[0]) and not isinstance(arg[0], type) and arg[0].__class__.__qualname__ not in dataclass_sources:
                result.append(inspect.getsource(arg[0].__class__))

        for _, v in kwargs.items():
            if is_dataclass(v) and not isinstance(v, type) and v.__class__.__qualname__ not in dataclass_sources:
                result.append(inspect.getsource(v.__class__))
                
        return result

class IfCallSite(CallSite):
    """
    The caller node is an ast.If node

    Example:
    if await llm.reason(...):
        ...
    """
    def _parse_return_type(self) -> Type:
        return BoolType(None)

class WhileCallSite(CallSite):
    """
    The caller node is an ast.While node

    Example:
    while await llm.reason(...):
        ...
    """
    def _parse_return_type(self) -> Type:
        return BoolType(None)

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
            tuple_type = TupleType(None, None)
            item_types = [AnyType(tuple_type) for _ in range(elts_len)]
            # let large language model to infer the type of each item in the tuple from the code context
            tuple_type._item_types = item_types
            return tuple_type
        
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
            return AnyType(None)
        
        annotation = declaration_node.annotation
        type = Type.from_annotation(annotation, self, None)
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
        type = Type.from_annotation(annotation, self, None)
        if type:
            return type

        raise RuntimeError(f"Cannot parse return type at line {self._absolute_call_line_number} for method {self._method_name} in {self._module_filename}")
    
class ReturnCallSite(CallSite):
    """
    The caller node is an ast.Return node

    Example:
    async def f() -> int:
        llm = LLM()
        return await llm.reason(...)
    """
    def _parse_return_type(self) -> Type:
        # self._caller_node is an ast.Return node, 
        # so we need to walk up the AST tree to find the return type annotation of the enclosing function
        # and we assume the enclosing function is the first ast.FunctionDef node we encounter when walking up the AST tree
        parent: ast.AsyncFunctionDef = None
        for node in ast.walk(self._tree):
            if isinstance(node, ast.AsyncFunctionDef):
                parent = node
                break

        if not parent:
            raise RuntimeError(f"Cannot find enclosing function for return statement at line {self._absolute_call_line_number} in {self._module_filename}")
        
        if not parent.returns:
            return AnyType()
        
        type = Type.from_annotation(parent.returns, self, None)
        if type:
            return type
        
        raise RuntimeError(f"Cannot parse return type at line {self._absolute_call_line_number} for method {self._method_name} in {self._module_filename}")