import ast
import hashlib
import sys
import inspect
from types import FrameType, FunctionType, MethodType, ModuleType
from typing import Optional, Union, Any, List, Tuple, Set, Type, Dict
from dataclasses import is_dataclass

from pydantic import BaseModel

from npllm.core.call_site_return_type import CallSiteReturnType
from npllm.core.call_site_ctx import CallSiteCtx
from npllm.core.call_site_contexts.ann_assign_ctx import AnnAssignCtx
from npllm.core.call_site_contexts.assign_ctx import AssignCtx
from npllm.core.call_site_contexts.if_ctx import IfCtx
from npllm.core.call_site_contexts.return_ctx import ReturnCtx
from npllm.core.call_site_contexts.while_ctx import WhileCtx
from npllm.utils.source_util import remove_indentation
from npllm.utils.inspect_util import get_class_from_module, is_module_frame
from npllm.core.notebook import Notebook, Cell

import logging

logger = logging.getLogger(__name__)

class CallSite:
    _call_site_cache: Dict['CallSite', 'CallSite'] = {}

    @classmethod
    def of(cls, caller_frame: FrameType, method_name: str, is_async: bool) -> 'CallSite':
        call_site = cls(caller_frame, method_name, is_async)
        if not call_site.in_notebook() and call_site in cls._call_site_cache:
            logger.info(f"Returning cached initialized {call_site}")
            return CallSite._call_site_cache[call_site]
        else:
            logger.info(f"Initializing {call_site}")
            call_site.initialize()
            logger.info(f"Initialized {call_site}")
            cls._call_site_cache[call_site] = call_site
            return call_site

    def __init__(
        self,
        caller_frame: FrameType,
        method_name: str,
        is_async: bool
    ):
        self._caller_frame = caller_frame

        self.enclosing_module: Union[ModuleType, Cell] = None
        self.module_filename: str = None
        if self.in_notebook():
            self.enclosing_module = Notebook.current_exec_cell()
            self.module_filename = self.enclosing_module.fake_module_filename()
        else:
            module_name = self._caller_frame.f_globals.get('__name__')
            self.enclosing_module = sys.modules[module_name]
            self.module_filename = self.enclosing_module.__file__

        self.line_number = caller_frame.f_lineno
        self.method_name = method_name

        self._is_async = is_async

        self.enclosing_function: Optional[Union[FunctionType, MethodType]] = None
        self.enclosing_class: Optional[Type] = None

        self.enclosing_function_source: Optional[str] = None
        self.enclosing_class_source: Optional[str] = None
        self.enclosing_module_source: Optional[str] = None

        self.enclosing_function_def: Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]] = None
        self.enclosing_class_def: Optional[ast.ClassDef] = None

        self._node: ast.Call = None
        self._ctx = None
        
        self.return_type: CallSiteReturnType = None
        self.positional_parameters: List[Tuple[int, CallSiteReturnType]] = None
        self.keyword_parameters: List[Tuple[str, CallSiteReturnType]] = None

        self.dependent_modules: Dict[str, Union[ModuleType, Cell]] = None

    def initialize(self):
        self._parse_enclosing_function()
        self._parse_enclosing_class()

        self._parse_enclosing_module_source()
        self._parse_enclosing_class_source()
        self._parse_enclosing_function_source()

        self._parse_enclosing_function_def()
        self._parse_enclosing_class_def()
        self._parse_enclosing_module_def()

        self._parse_ctx()
        
        self._parse_positional_parameters()
        self._parse_keyword_parameters()

        self._parse_dependent_modules()

    def _minimal_enclosing_source_and_relative_line_number(self) -> str:
        if self.enclosing_function:
            return self.enclosing_function_source, self.line_number - self._caller_frame.f_code.co_firstlineno + 1
        else:
            return self.enclosing_module_source, self.line_number

    def _parse_ctx(self) -> CallSiteCtx:
        ctx = None
        minimal_enclosing_source, relative_line_number = self._minimal_enclosing_source_and_relative_line_number()
        for node in ast.walk(ast.parse(minimal_enclosing_source)):
            if hasattr(node, 'lineno') and node.lineno == relative_line_number:
                if self._is_async:
                    if isinstance(node, ast.If) and isinstance(node.test, ast.Await) and node.test.value.func.attr == self.method_name:
                        ctx = IfCtx(self)
                        self._node = node.test.value
                    elif isinstance(node, ast.While) and isinstance(node.test, ast.Await) and node.test.value.func.attr == self.method_name:
                        ctx = WhileCtx(self)
                        self._node = node.test.value
                    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == self.method_name:
                        ctx = AssignCtx(self, node)
                        self._node = node.value.value
                    elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == self.method_name:
                        ctx = AnnAssignCtx(self, node)
                        self._node = node.value.value
                    elif isinstance(node, ast.Return) and isinstance(node.value, ast.Await) and node.value.value.func.attr == self.method_name:
                        ctx = ReturnCtx(self)
                        self._node = node.value.value
                else:
                    if isinstance(node, ast.If) and isinstance(node.test, ast.Call) and node.test.func.attr == self.method_name:
                        self._node = node.test.value
                        ctx = IfCtx(self)
                    elif isinstance(node, ast.While) and isinstance(node.test, ast.Call) and node.test.func.attr == self.method_name:
                        ctx = WhileCtx(self)
                        self._node = node.test.value
                    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and node.value.func.attr == self.method_name:
                        ctx = AssignCtx(self, node)
                        self._node = node.value
                    elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call) and node.value.func.attr == self.method_name:
                        self._node = node.value
                        ctx = AnnAssignCtx(self, node)
                    elif isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and node.value.func.attr == self.method_name:
                        ctx = ReturnCtx(self)
                        self._node = node.value

        if ctx:
            self._ctx = ctx
            self.return_type = ctx.return_type
            logger.info(f"Return type for {self}: {self.return_type}")
        else:
            raise RuntimeError(f"Call site context for {self} is not supported yet")

    def _parse_dependent_modules(self):
        dependent_modules = {}
        dependent_modules.update({self.module_filename: self.enclosing_module})
        dependent_modules.update(self.return_type.get_dependent_modules())
        for _, arg_type in self.positional_parameters + self.keyword_parameters:
            dependent_modules.update(arg_type.get_dependent_modules())
        
        logger.info(f"Dependent modules for {self}: {dependent_modules}")
        self.dependent_modules = dependent_modules

    def _parse_positional_parameters(self) -> List[Tuple[int, CallSiteReturnType]]:
        self.positional_parameters = self._parse_args_types([(i, arg) for i, arg in enumerate(self._node.args)])

    def _parse_keyword_parameters(self) -> List[Tuple[str, CallSiteReturnType]]:
        self.keyword_parameters = self._parse_args_types([(kw.arg, kw.value) for kw in self._node.keywords])

    def _parse_args_types(self, args) -> List[Tuple[Union[int, str], CallSiteReturnType]]:
        args_types = []
        for arg_name, arg in args:
            annotation = None
            if isinstance(arg, ast.Constant):
                annotation = arg
            else:
                if isinstance(arg, ast.Name):
                    var_name = arg.id
                elif isinstance(arg, ast.Attribute) and arg.value.id == 'self':
                    var_name = f"self.{arg.attr}"
                else:
                    raise RuntimeError(f"Unsupported argument type: {ast.dump(arg)}")

                declaration_node = self.get_annotated_declaration_node(var_name)
                if not declaration_node:
                    raise RuntimeError(f"Cannot get annotated declaration node for variable {var_name} at {self}")

                annotation = declaration_node.annotation

            arg_type = CallSiteReturnType.from_annotation(annotation, self)
            if not arg_type:
                raise RuntimeError(f"Cannot parse argument type for {var_name} at {self}")

            args_types.append((arg_name, arg_type))

        return args_types

    def get_annotated_declaration_node(self, var_name: str) -> Optional[ast.AnnAssign]:
        if var_name.startswith('self.'):
            # find annotated declaration node in the enclosing class
            enclosing_class_def = self._get_enclosing_class_def()
            if not enclosing_class_def:
                return None
            
            for node in ast.walk(enclosing_class_def):
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
                    if f"{node.target.value.id}.{node.target.attr}" == var_name:
                        return node
        else:
            # find annotated declaration node in the enclosing function
            enclosing_function_def = self._get_enclosing_function_def()
            if not enclosing_function_def:
                return None
            
            for node in ast.walk(enclosing_function_def):
                if isinstance(node, ast.AnnAssign) and node.target.id == var_name:
                    return node

            for arg in enclosing_function_def.args.args:
                if arg.arg == var_name:
                    return arg

            # find annotated declaration node in the enclosing module
            for node in ast.walk(ast.parse(self.get_module_source(self.enclosing_module))):
                if isinstance(node, ast.AnnAssign) and node.target.id == var_name:
                    return node

        return None

    def _parse_enclosing_function(self):
        if is_module_frame(self._caller_frame):
            return
        
        code_name = self._caller_frame.f_code.co_name

        if "self" in self._caller_frame.f_locals:
            self_obj = self._caller_frame.f_locals['self']
            method = getattr(self_obj, code_name)
            if isinstance(method, MethodType):
                if method.__func__.__code__ == self._caller_frame.f_code:
                    self.enclosing_function = method
        else:
            if code_name in self._caller_frame.f_globals:
                func = self._caller_frame.f_globals[code_name]
                if isinstance(func, FunctionType):
                    if '.' not in func.__qualname__:
                        self.enclosing_function = func

    def _parse_enclosing_class(self):
        if self.enclosing_function and isinstance(self.enclosing_function, MethodType):
            self.enclosing_class = self.enclosing_function.__self__.__class__

    def _parse_enclosing_function_source(self):
        if self.enclosing_function:
            self.enclosing_function_source = self.get_function_source(self.enclosing_function)

    def _parse_enclosing_class_source(self):
        if self.enclosing_class:
            self.enclosing_class_source = self.get_class_source(self.enclosing_class)

    def _parse_enclosing_module_source(self):
        self.enclosing_module_source = self.get_module_source(self.enclosing_module)

    def _parse_enclosing_function_def(self):
        if self.enclosing_function:
            for node in ast.walk(ast.parse(self.enclosing_function_source)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == self.enclosing_function.__name__:
                    self.enclosing_function_def = node
                    return

    def _parse_enclosing_class_def(self):
        if self.enclosing_class:
            for node in ast.walk(ast.parse(self.enclosing_class_source)):
                if isinstance(node, ast.ClassDef) and node.name == self.enclosing_class.__name__:
                    self.enclosing_class_def = node
                    return

    def _parse_enclosing_module_def(self):
        for node in ast.walk(ast.parse(self.enclosing_module_source)):
            if isinstance(node, ast.Module):
                self.enclosing_module_def = node
                return
    
    def get_cls_defining_module(self, cls: Type) -> Optional[Union[ModuleType, Cell]]:
        return inspect.getmodule(cls)

    def get_class(self, class_name: str, enclosing_class: Optional[Type]=None) -> Optional[Type]:
        klass = get_class_from_module(class_name, self.enclosing_module)
        if klass and (is_dataclass(klass) or issubclass(klass, BaseModel)):
            return klass

        if enclosing_class:
            enclosing_class_module = inspect.getmodule(enclosing_class)
            if enclosing_class_module:
                klass = get_class_from_module(class_name, enclosing_class_module)
                if klass and (is_dataclass(klass) or issubclass(klass, BaseModel)):
                    return klass

        return None

    def get_module_source(self, module: Union[ModuleType, Cell]) -> str:
        if isinstance(module, Cell):
            return module.code
        else:
            return inspect.getsource(module)

    def get_class_source(self, cls: Type) -> str:
        return remove_indentation(inspect.getsource(cls))

    def get_function_source(self, func: Union[FunctionType, MethodType]) -> str:
        return remove_indentation(inspect.getsource(func))

    def in_notebook(self) -> bool:
        return "ipykernel" in inspect.getfile(self._caller_frame)

    def __hash__(self) -> int:
        return hash((self.module_filename, self.line_number, self.method_name))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CallSite):
            return False

        return (
            self.module_filename == other.module_filename and 
            self.line_number == other.line_number and 
            self.method_name == other.method_name
        )

    def __str__(self) -> str:
        return f"CallSite[{self.module_filename}:{self.line_number}:{self.method_name}]"