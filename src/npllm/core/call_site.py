import ast
import inspect
import typing
from abc import abstractmethod
from types import FrameType, FunctionType, MethodType, ModuleType
from typing import Optional, Union, Any, Dict, List, Tuple, Set
from dataclasses import dataclass, is_dataclass

from pydantic import BaseModel

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext
from npllm.utils.source_util import remove_indentation
from npllm.utils.inspect_util import get_class_from_module, get_global_function_object, get_instance_method_object, get_module_object

import logging

logger = logging.getLogger(__name__)

@dataclass
class CallSiteIdentifier:
    module_filename: str
    line_number: int
    method_name: str

    def __hash__(self):
        return hash((self.module_filename, self.line_number, self.method_name))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CallSiteIdentifier):
            return False

        return self.module_filename == other.module_filename and self.line_number == other.line_number and self.method_name == other.method_name

    def __str__(self) -> str:
        return f"CallSite[{self.module_filename}:{self.line_number}:{self.method_name}]"

    def to_cache_filename(self) -> str:
        module_filename = self.module_filename.replace("/", "__SLASH__")
        return f"{module_filename}#{self.line_number}#{self.method_name}.xml"

    @classmethod
    def from_cache_filename(cls, cache_filename: str) -> 'CallSiteIdentifier':
        module_filename = cache_filename.split("#")[0].replace("__SLASH__", "/")
        line_number = int(cache_filename.split("#")[1])
        method_name = cache_filename.split("#")[2].split(".")[0]
        return CallSiteIdentifier(module_filename, line_number, method_name)

class CallSite(RuntimeContext):
    _call_site_cache: Dict[CallSiteIdentifier, 'CallSite'] = {}

    @classmethod
    def create_identifier(cls, caller_frame: FrameType, method_name: str) -> CallSiteIdentifier:
        module_object = get_module_object(caller_frame)
        assert module_object
        if "ipykernel" in inspect.getfile(caller_frame):
            return CallSiteIdentifier(inspect.getfile(caller_frame), caller_frame.f_lineno, method_name)
        return CallSiteIdentifier(module_object.__file__, caller_frame.f_lineno, method_name)

    @classmethod
    def of(
        cls, 
        caller_frame: FrameType, 
        method_name: str,
        is_async: bool
    ) -> 'CallSite':
        identifier = cls.create_identifier(caller_frame, method_name)
        if identifier in cls._call_site_cache:
            logger.info(f"Get call site from cache: {identifier}")
            return cls._call_site_cache[identifier]

        enclosing_source = None
        relative_line_number = None
        absolute_line_number = caller_frame.f_lineno
        if caller_frame.f_code.co_name == "<module>":
            enclosing_source = remove_indentation(inspect.getsource(inspect.getmodule(caller_frame)))
            relative_line_number = caller_frame.f_lineno
        else:
            enclosing_source = remove_indentation(inspect.getsource(caller_frame.f_code))
            relative_line_number = absolute_line_number - caller_frame.f_code.co_firstlineno + 1

        from npllm.core.call_sites.if_call_site import IfCallSite
        from npllm.core.call_sites.while_call_site import WhileCallSite
        from npllm.core.call_sites.assign_call_site import AssignCallSite
        from npllm.core.call_sites.ann_assign_call_site import AnnAssignCallSite
        from npllm.core.call_sites.return_call_site import ReturnCallSite
        
        call_site = None
        for node in ast.walk(ast.parse(enclosing_source)):
            if hasattr(node, 'lineno') and node.lineno == relative_line_number:
                if is_async:
                    if isinstance(node, ast.If) and isinstance(node.test, ast.Await) and node.test.value.func.attr == method_name:
                        call_site = IfCallSite(identifier, caller_frame, method_name, node.test.value)
                    elif isinstance(node, ast.While) and isinstance(node.test, ast.Await) and node.test.value.func.attr == method_name:
                        call_site = WhileCallSite(identifier, caller_frame, method_name, node.test.value)
                    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                        call_site = AssignCallSite(identifier, caller_frame, method_name, node.value.value, node)
                    elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                        call_site = AnnAssignCallSite(identifier, caller_frame, method_name, node.value.value, node)
                    elif isinstance(node, ast.Return) and isinstance(node.value, ast.Await) and node.value.value.func.attr == method_name:
                        call_site = ReturnCallSite(identifier, caller_frame, method_name, node.value.value)

                    if not call_site and isinstance(node, ast.Call) and node.func.attr == method_name:
                        raise RuntimeError(f"Call site for method {method_name} at line {absolute_line_number} in {inspect.getmodule(caller_frame).__file__} is not supported yet")
                else:
                    if isinstance(node, ast.If) and isinstance(node.test, ast.Call) and node.test.func.attr == method_name:
                        call_site = IfCallSite(identifier, caller_frame, method_name, node.test)
                    elif isinstance(node, ast.While) and isinstance(node.test, ast.Call) and node.test.func.attr == method_name:
                        call_site = WhileCallSite(identifier, caller_frame, method_name, node.test)
                    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and node.value.func.attr == method_name:
                        call_site = AssignCallSite(identifier, caller_frame, method_name, node.value, node)
                    elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call) and node.value.func.attr == method_name:
                        call_site = AnnAssignCallSite(identifier, caller_frame, method_name, node.value, node)
                    elif isinstance(node, ast.Return) and isinstance(node.value, ast.Call) and node.value.func.attr == method_name:
                        call_site = ReturnCallSite(identifier, caller_frame, method_name, node.value)

                    if not call_site and isinstance(node, ast.Call) and node.func.attr == method_name:
                        raise RuntimeError(f"Call site for method {method_name} at line {absolute_line_number} in {inspect.getmodule(caller_frame).__file__} is not supported yet")

        if call_site:
            logger.info(f"Create a new call site and cache it: {identifier}")
            cls._call_site_cache[identifier] = call_site
            return call_site

        raise RuntimeError(f"Cannot find call site for method {method_name} at line {absolute_line_number} in {inspect.getmodule(caller_frame).__file__}")
    
    def __init__(
        self,
        identifier: CallSiteIdentifier,
        caller_frame: FrameType,
        method_name: str,
        call_node: ast.Call
    ):
        self._identifier = identifier
        self._caller_frame = caller_frame
        self._method_name = method_name
        self._call_node = call_node

        self._enclosing_function: Optional[Union[FunctionType, MethodType]] = self._parse_enclosing_function()
        self._enclosing_class: Optional[Type] = self._parse_enclosing_class()
        self._enclosing_module: Optional[ModuleType] = self._parse_enclosing_module()
        self._return_type: Type = self.parse_return_type()
        self._positional_parameters: List[Tuple[int, str]] = self._parse_positional_parameters()
        self._keyword_parameters: List[Tuple[str, str]] = self._parse_keyword_parameters()
        self._args_types: List[Tuple[Union[int, str], Type]] = self._positional_parameters + self._keyword_parameters
        self._dependent_modules: List[ModuleType] = self._parse_dependent_modules()

    @abstractmethod
    def parse_return_type(self) -> Type:
        pass

    def _parse_dependent_modules(self) -> Set[ModuleType]:
        dependent_modules = set()
        dependent_modules.add(self.enclosing_module)
        dependent_modules.update(self.return_type.get_dependent_modules())
        for _, arg_type in self._args_types:
            dependent_modules.update(arg_type.get_dependent_modules())
        return dependent_modules

    def _parse_positional_parameters(self) -> List[Tuple[int, str]]:
        return self._parse_args_types([(i, arg) for i, arg in enumerate(self._call_node.args)])

    def _parse_keyword_parameters(self) -> List[Tuple[str, str]]:
        return self._parse_args_types([(kw.arg, kw.value) for kw in self._call_node.keywords])

    def _parse_args_types(self, args) -> List[Tuple[Union[int, str], Type]]:
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

                declaration_node = self._find_annotated_declaration_node(var_name)
                if not declaration_node:
                    raise RuntimeError(f"Cannot find declaration node for variable {var_name} at call site {self}")

                annotation = declaration_node.annotation

            arg_type = Type.from_annotation(annotation, self)
            if not arg_type:
                raise RuntimeError(f"Cannot parse argument type for {var_name} at call site {self}")

            args_types.append((arg_name, arg_type))

        return args_types

    def _find_annotated_declaration_node(self, var_name: str) -> Optional[ast.AnnAssign]:
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

    def _parse_enclosing_function(self) -> Optional[Union[FunctionType, MethodType]]:
        # for now, we only support global function and class instance method
        # IMPORTANT: this means that llm can only be called on global function or class instance method
        return get_global_function_object(self._caller_frame) or get_instance_method_object(self._caller_frame) or None

    def _parse_enclosing_class(self) -> Optional[Type]:
        if not self.enclosing_function:
            return None
        
        if isinstance(self.enclosing_function, MethodType):
            return self.enclosing_function.__self__.__class__

        return None

    def _parse_enclosing_module(self) -> Optional[ModuleType]:
        return get_module_object(self._caller_frame)

    @property
    def dependent_modules(self) -> Set[ModuleType]:
        return self._dependent_modules

    @property
    def return_type(self) -> Type:
        return self._return_type

    @property
    def positional_parameters(self) -> List[Tuple[int, str]]:
        return self._positional_parameters

    @property
    def keyword_parameters(self) -> List[Tuple[str, str]]:
        return self._keyword_parameters

    @property
    def args_types(self) -> List[Tuple[Union[int, str], Type]]:
        return self._args_types

    @property
    def enclosing_function(self) -> Optional[Union[FunctionType, MethodType]]:
        return self._enclosing_function

    @property
    def enclosing_class(self) -> Optional[typing.Type]:
        return self._enclosing_class

    @property
    def enclosing_module(self) -> Optional[ModuleType]:
        return self._enclosing_module

    def _get_enclosing_function_def(self) -> Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]]:
        if not self.enclosing_function:
            return None
            
        func_source = self.get_function_source(self.enclosing_function)
        for node in ast.walk(ast.parse(func_source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == self.enclosing_function.__name__:
                return node
        return None

    def _get_enclosing_class_def(self) -> Optional[ast.ClassDef]:
        if not self.enclosing_class:
            return None
        
        class_source = self.get_class_source(self.enclosing_class)
        for node in ast.walk(ast.parse(class_source)):
            if isinstance(node, ast.ClassDef) and node.name == self.enclosing_class.__name__:
                return node
        return None

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

    def get_module_source(self, module: ModuleType) -> str:
        return remove_indentation(inspect.getsource(module))

    def get_class_source(self, cls: Type) -> str:
        return remove_indentation(inspect.getsource(cls))

    def get_function_source(self, func: Union[FunctionType, MethodType]) -> str:
        return remove_indentation(inspect.getsource(func))

    def in_notebook(self) -> bool:
        return "ipykernel" in inspect.getfile(self._caller_frame)

    @property
    def identifier(self) -> CallSiteIdentifier:
        return self._identifier

    def __hash__(self) -> int:
        return hash(self._identifier)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CallSite):
            return False

        return self._identifier == other._identifier

    def __str__(self) -> str:
        return str(self._identifier)