import inspect
from abc import ABC, abstractmethod
import traceback
import typing
from typing import Literal, Dict, Union, List, Any, Optional, Tuple
from types import UnionType as types_UnionType
import ast
from dataclasses import fields
import logging

from npllm.utils.notebook_util import get_dataclass_source
from npllm.utils.source_util import remove_indentation

logger = logging.getLogger(__name__)

class ValueConversionError(Exception):
    pass

class Type(ABC):
    @classmethod
    def from_annotation(cls, annotation: ast.AST, call_site, parent_type) -> 'Type':
        """
        Create a Type instance from an AST annotation node

        Example:
        x: int -> BasicType("int")
        y: List[int] -> ListType(BasicType("int"))
        """
        result = None
        if isinstance(annotation, ast.Name) or isinstance(annotation, ast.Constant):
            result = (
                BasicType.from_annotation(annotation, call_site, parent_type) or 
                AnyType.from_annotation(annotation, call_site, parent_type) or 
                DataclassType.from_annotation(annotation, call_site, parent_type) or 
                AliasType.from_annotation(annotation, call_site, parent_type)
            )
        elif isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
            base_type = annotation.value.id
            if base_type == 'List' or base_type == 'list':
                result = ListType.from_annotation(annotation, call_site, parent_type)
            elif base_type == 'Tuple' or base_type == 'tuple':
                result = TupleType.from_annotation(annotation, call_site, parent_type)
            elif base_type == 'Dict' or base_type == 'dict':
                result = DictType.from_annotation(annotation, call_site, parent_type)
            elif base_type == 'Union' or base_type == 'union':
                result = UnionType.from_annotation(annotation, call_site, parent_type)
            elif base_type == 'Literal' or base_type == 'literal':
                result = LiteralType.from_annotation(annotation, call_site, parent_type)
            elif base_type == 'Optional' or base_type == 'optional':
                result = OptionalType.from_annotation(annotation, call_site, parent_type)
        elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}...")
            left_type = Type.from_annotation(annotation.left, call_site, parent_type)
            right_type = Type.from_annotation(annotation.right, call_site, parent_type)
            if left_type and right_type:
                logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                result = UnionType(parent_type, [left_type, right_type])
        
        return result
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> 'Type':
        if type(py_type) is typing.ForwardRef:
            logger.debug(f"Type.from_python_type: resolving ForwardRef {py_type}...")
            ref = py_type.__forward_arg__
            # only find the forward ref in the module of the call site for simplicity
            module = call_site.get_module()
            if module and hasattr(module, ref):
                py_type = getattr(module, ref)
                logger.debug(f"Type.from_python_type: resolved ForwardRef {ref} to {py_type}")
            else:
                logger.warning(f"Type.from_python_type: cannot resolve ForwardRef {py_type}")
                return None

        return (
            BasicType.from_python_type(py_type, call_site, parent_type) or
            ListType.from_python_type(py_type, call_site, parent_type) or
            TupleType.from_python_type(py_type, call_site, parent_type) or
            # place OptionalType before UnionType to handle Optional[T] correctly
            OptionalType.from_python_type(py_type, call_site, parent_type) or
            AliasType.from_python_type(py_type, call_site, parent_type) or
            DictType.from_python_type(py_type, call_site, parent_type) or
            UnionType.from_python_type(py_type, call_site, parent_type) or
            AnyType.from_python_type(py_type, call_site, parent_type) or
            LiteralType.from_python_type(py_type, call_site, parent_type) or
            DataclassType.from_python_type(py_type, call_site, parent_type) or
            AliasType.from_python_type(py_type, call_site, parent_type) or None
        )
    
    def __init__(self, parent_type):
        self._parent_type = parent_type
    
    @abstractmethod
    def convert(self, value: Any, field_path: str=None):
        """
        Convert a JSON value to the target type value

        If conversion fails, raise ValueConversionError with a descriptive message which is llm friendly
        """
        pass

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        return {}

    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        return {}

    @abstractmethod
    def __repr__(self):
        pass

class BasicType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['BasicType']:
        if isinstance(annotation, ast.Name) and annotation.id in ('str', 'int', 'float', 'bool'):
            return BasicType(parent_type, annotation.id)
        if isinstance(annotation, ast.Constant) and annotation.value in ('str', 'int', 'float', 'bool'):
            return BasicType(parent_type, annotation.value)
        return None
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['BasicType']:
        if py_type in (str, int, float, bool):
            logger.debug(f"BasicType.from_python_type: {py_type}")
            return BasicType(parent_type, py_type.__name__)
        return None
    
    def __init__(self, parent_type, type: Literal["str", "int", "float", "bool"]):
        Type.__init__(self, parent_type)
        self._type = type

    def convert(self, value, field_path, strict=False):
        if strict:
            return self.convert_strict(value, field_path)
        
        if value is None:
            return None
    
        if self._type == "str":
            return str(value)

        if value == "":
            return None

        if self._type == "int":
            return int(value)
        elif self._type == "float":
            return float(value)
        elif self._type == "bool":
            return bool(value)
        
        raise RuntimeError(f"Unknown basic type: {self._type}")
    
    def convert_strict(self, value, field_path):
        if value is None:
            return None
        
        if self._type == "str":
            if not isinstance(value, str):
                raise ValueConversionError(f"{field_path} expected to be str, but got {type(value).__name__}")
            return value

        if self._type in ("int", "float"):
            if not isinstance(value, int) and not isinstance(value, float):
                raise ValueConversionError(f"{field_path} expected to be int or float, but got {type(value).__name__}")
            return value
        
        elif self._type == "bool":
            if not isinstance(value, bool):
                raise ValueConversionError(f"{field_path} expected to be bool, but got {type(value).__name__}")
            return value
        
        raise RuntimeError(f"Unknown basic type: {self._type}")

    def __repr__(self):
        return f"{self._type}"
    
class ListType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site, parent_type) -> Optional['ListType']:
        logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}...")
        list_type = ListType(parent_type, None)
        item_type = Type.from_annotation(annotation.slice, call_site, list_type)
        if item_type:
            list_type._item_type = item_type
            logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}")
            return list_type
        return None
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['ListType']:
        list_type = ListType(parent_type, None)
        origin = typing.get_origin(py_type)
        args = typing.get_args(py_type)
        if origin in (list, List) and len(args) == 1:
            logger.debug(f"ListType.from_python_type: {py_type}...")
            item_type = Type.from_python_type(args[0], call_site, list_type)
            if item_type:
                logger.debug(f"ListType.from_python_type: {py_type}")
                list_type._item_type = item_type
                return list_type
        return None

    def __init__(self, parent_type, item_type: 'Type'):
        Type.__init__(self, parent_type)
        self._item_type = item_type

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        return self._item_type.related_dataclass_sources(visited)
    
    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        return self._item_type.type_alias_sources(visited)

    def convert(self, value, field_path: str, strict=False):
        if value is None:
            return None
        
        if not isinstance(value, List):
            raise ValueConversionError(f"{field_path} expected to be a list")

        converted_list = []
        for i, item in enumerate(value):
            converted_item = self._item_type.convert(item, f"{field_path}[{i}]", strict)
            converted_list.append(converted_item)
        return converted_list

    def __repr__(self):
        return f"List[{self._item_type}]"
    
class TupleType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site, parent_type) -> Optional['TupleType']:
        logger.debug(f"TupleType.from_annotation: {ast.dump(annotation)}...")
        tuple_type = TupleType(parent_type, None)
        item_types = []
        for elt in annotation.slice.elts:
            item_type = Type.from_annotation(elt, call_site, tuple_type)
            if item_type:
                item_types.append(item_type)
            else:
                return None
        tuple_type._item_types = tuple(item_types)
        logger.debug(f"TupleType.from_annotation: {ast.dump(annotation)}")
        return tuple_type
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['TupleType']:
        origin = typing.get_origin(py_type)
        args = typing.get_args(py_type)
        if origin in (tuple, Tuple) and len(args) >= 1:
            logger.debug(f"TupleType.from_python_type: {py_type}...")
            tuple_type = TupleType(parent_type, None)
            item_types = []
            for arg in args:
                item_type = Type.from_python_type(arg, call_site, tuple_type)
                if item_type:
                    item_types.append(item_type)
                else:
                    return None
            tuple_type._item_types = tuple(item_types)
            logger.debug(f"TupleType.from_python_type: {py_type}")
            return tuple_type
        
        return None

    def __init__(self, parent_type, item_types: tuple['Type', ...]):
        Type.__init__(self, parent_type)
        self._item_types = item_types

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        result = {}
        for item_type in self._item_types:
            result.update(item_type.related_dataclass_sources(visited))
        return result
    
    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        result = {}
        for item_type in self._item_types:
            result.update(item_type.type_alias_sources(visited))
        return result
    
    def convert(self, value, field_path: str, strict=False):
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValueConversionError(f"{field_path} expected to be a list")

        if len(self._item_types) != len(value):
            raise ValueConversionError(f"{field_path} expected to have {len(self._item_types)} items, but got {len(value)} items")

        converted_list = []
        for i, item_type in enumerate(self._item_types):
            converted_item = item_type.convert(value[i], f"{field_path}[{i}]", strict)
            converted_list.append(converted_item)
        return tuple(converted_list)


    def __repr__(self):
        items_repr = []
        for item in self._item_types:
            items_repr.append(repr(item))
        return f"Tuple[{', '.join(items_repr)}]"

class DictType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site, parent_type) -> Optional['DictType']:
        logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}...")
        dict_type = DictType(parent_type, None, None)
        key_type = Type.from_annotation(annotation.slice.elts[0], call_site, dict_type)
        value_type = Type.from_annotation(annotation.slice.elts[1], call_site, dict_type)
        if key_type and value_type:
            if not isinstance(key_type, BasicType) or key_type._type != 'str':
                raise RuntimeError("Only str key type is supported in Dict")
            dict_type._key_type = key_type
            dict_type._value_type = value_type
            logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}")
            return dict_type
        return None

    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['DictType']:
        origin = typing.get_origin(py_type)
        args = typing.get_args(py_type)
        if origin in (dict, Dict) and len(args) == 2:
            logger.debug(f"DictType.from_python_type: {py_type}...")
            dict_type = DictType(parent_type, None, None)
            key_type = Type.from_python_type(args[0], call_site, dict_type)
            value_type = Type.from_python_type(args[1], call_site, dict_type)
            if key_type and value_type:
                if not isinstance(key_type, BasicType) or key_type._type != 'str':
                    raise RuntimeError("Only str key type is supported in Dict")
                
                dict_type._key_type = key_type
                dict_type._value_type = value_type
                logger.debug(f"DictType.from_python_type: {py_type}")
                return dict_type
        return None

    def __init__(self, parent_type, key_type: 'Type', value_type: 'Type'):
        Type.__init__(self, parent_type)
        self._key_type = key_type
        self._value_type = value_type

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        result = {}
        result.update(self._key_type.related_dataclass_sources(visited))
        result.update(self._value_type.related_dataclass_sources(visited))
        return result
    
    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        result = {}
        result.update(self._key_type.type_alias_sources(visited))
        result.update(self._value_type.type_alias_sources(visited))
        return result
    
    def convert(self, value, field_path: str, strict=False):
        if value is None:
            return None

        if not isinstance(value, Dict):
            raise ValueConversionError(f"{field_path} expected to be a dict")

        converted_dict = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueConversionError(f"{field_path} expected to have string keys, but got key of type {type(k).__name__}")
            converted_value = self._value_type.convert(v, f"{field_path}.{k}", strict)
            converted_dict[k] = converted_value
        return converted_dict

    def __repr__(self):
        return f"Dict[{self._key_type}, {self._value_type}]"

class DataclassType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['DataclassType']:
        class_name = annotation.id if isinstance(annotation, ast.Name) else annotation.value
        # get the parent dataclass from parent_type chain
        parent_dataclass = None
        current = parent_type
        while current:
            if isinstance(current, DataclassType):
                parent_dataclass = current._dataclass_cls
                break
            current = current._parent_type
        
        dataclass_cls = call_site.get_dataclass(class_name, parent_dataclass)
        if not dataclass_cls:
            return None
        
        logger.debug(f"DataclassType.from_annotation: {ast.dump(annotation)}...")
        # check parent_type chain for self-referencing dataclass
        if parent_type:
            current = parent_type
            while current:
                if isinstance(current, DataclassType) and current._dataclass_cls == dataclass_cls:
                    logger.debug(f"DataclassType.from_annotation: {class_name} is self-referencing")
                    return current
                current = current._parent_type
        
        # get the source of the dataclass
        dataclass_source = remove_indentation(call_site.get_dataclass_source(dataclass_cls))
        if not dataclass_source:
            return None

        dataclass_type = DataclassType(parent_type, dataclass_cls, None, call_site)
        logger.debug(f"DataclassType.from_annotation: early created DataclassType for {class_name} for self referencing")
        # we have to handle field types by analyzing the source code of the dataclass
        # because directly using field's python type some type alias name may be lost, for example:
        # 
        # Type = Union[int, str]
        # @dataclass
        # class Demo:
        #   value: Type # here alias name 'Type' is lost if we directly use field.type
        tree = ast.parse(dataclass_source)
        field_types = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        field_name = stmt.target.id
                        field_type = Type.from_annotation(stmt.annotation, call_site, dataclass_type)
                        if not field_type:
                            return None
                        field_types[field_name] = field_type
                
                dataclass_type._field_types = field_types
                logger.debug(f"DataclassType.from_annotation: {ast.dump(annotation)}")
                return dataclass_type 

        return None

    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['DataclassType']:
        if not py_type or not inspect.isclass(py_type) or not hasattr(py_type, '__dataclass_fields__'):
            return None
        
        logger.debug(f"DataclassType.from_python_type: {py_type}...")
        dataclass_cls = py_type

        # find self-referencing dataclass in parent_type chain
        if parent_type:
            current = parent_type
            while current:
                if isinstance(current, DataclassType) and current._dataclass_cls == dataclass_cls:
                    logger.debug(f"DataclassType.from_python_type: {py_type} is self-referencing")
                    return current
                current = current._parent_type
                

        field_types = {}
        # this is to handle self-referencing dataclass, like:
        # 
        # @dataclass
        # class Tree:
        #   value: int
        #   left: Optional['Tree']
        #   right: Optional['Tree']
        # 
        # we create a DataclassType instance first, then fill in the field types
        dataclass_type = DataclassType(parent_type, dataclass_cls, None, call_site)
        logger.debug(f"DataclassType.from_python_type: early created DataclassType for {py_type} for self referencing")
        for field in fields(dataclass_cls):
            field_type = Type.from_python_type(field.type, call_site, parent_type=dataclass_type)
            if not field_type:
                return None
            field_types[field.name] = field_type

        dataclass_type._field_types = field_types
        logger.debug(f"DataclassType.from_python_type: {py_type}")
        return dataclass_type
        

    def __init__(self, parent_type, dataclass_cls, field_types: Dict[str, 'Type'], call_site):
        Type.__init__(self, parent_type)
        self._dataclass_cls: typing.Type = dataclass_cls
        self._field_types = field_types
        self._call_site = call_site

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}

        visited.add(self)
        result = {}
        if self._call_site.is_in_notebook():
            # TODO notebook environment may has many issues, leave it for later
            result[self._dataclass_cls.__qualname__] = get_dataclass_source(self._dataclass_cls)
        else:
            result[self._dataclass_cls.__qualname__] = inspect.getsource(self._dataclass_cls)

        for field_type in self._field_types.values():
            result.update(field_type.related_dataclass_sources(visited))
            
        return result
    
    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        result = {}
        for field_type in self._field_types.values():
            result.update(field_type.type_alias_sources(visited))
        return result
    
    def convert(self, value, field_path: str, strict):
        if strict:
            return self.convert_strict(value, field_path)
        
        if value is None:
            return None
    
        if not isinstance(value, Dict):
            if type(value) in (int, float, str, bool) and len(self._field_types) == 1:
                # sometimes llm may return a primitive value directly for a dataclass with a single field
                logger.warning(f"{field_path} expected to be a dict, but got a primitive value: {value}, trying to convert it to the only field of the dataclass: {self}")
                only_field_name = list(self._field_types.keys())[0]
                value = {only_field_name: value}
            else:
                raise ValueConversionError(f"{field_path} expected to be a dict")
        
        field_values = {}
        for field_name, field_type in self._field_types.items():
            if field_name in value:
                field_value = field_type.convert(value[field_name], f"{field_path}.{field_name}", strict)
                field_values[field_name] = field_value
            else:
                field_values[field_name] = None

        return self._dataclass_cls(**field_values)
    
    def convert_strict(self, value, field_path):
        if value is None:
            return None
    
        if not isinstance(value, Dict):
            raise ValueConversionError(f"{field_path} expected to be a dict")
        
        field_values = {}
        for field_name, field_type in self._field_types.items():
            if field_name in value:
                field_value = field_type.convert(value[field_name], f"{field_path}.{field_name}", strict=True)
                field_values[field_name] = field_value
            else:
                raise ValueConversionError(f"{field_path} expected to have field {field_name}, but it's missing")

        return self._dataclass_cls(**field_values)

    def __repr__(self):
        return f"{self._dataclass_cls.__name__}"

class UnionType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site, parent_type) -> Optional['UnionType']:
        logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}...")
        union_type = UnionType(parent_type, None)
        if not hasattr(annotation.slice, 'elts'):
            type = Type.from_annotation(annotation.slice, call_site, union_type)
            if type:
                union_type._types = [type]
                logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                return union_type
            return None
        
        types = []
        for elt in annotation.slice.elts:
            type = Type.from_annotation(elt, call_site, parent_type)
            if type:
                types.append(type)
            else:
                return None
        union_type._types = types
        logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
        return union_type
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['UnionType']:
        origin = typing.get_origin(py_type)
        args = typing.get_args(py_type)
        if origin in (typing.Union, types_UnionType, typing._UnionGenericAlias) and len(args) >= 1:
            logger.debug(f"UnionType.from_python_type: {py_type}...")
            union_type = UnionType(parent_type, None)
            types = []
            for arg in args:
                arg_type = Type.from_python_type(arg, call_site, parent_type)
                if arg_type:
                    types.append(arg_type)
                else:
                    return None
            
            union_type._types = types
            logger.debug(f"UnionType.from_python_type: {py_type}")
            return union_type
        return None
        
    def __init__(self, parent_type, types: List['Type']):
        Type.__init__(self, parent_type)
        self._types = types

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}

        visited.add(self)
        result = {}
        for type in self._types:
            result.update(type.related_dataclass_sources(visited))
        return result
    
    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        result = {}
        for type in self._types:
            result.update(type.type_alias_sources(visited))
        return result
    
    def convert(self, value, field_path: str, strict=False):
        if strict:
            return self.convert_strict(value, field_path)
        
        if value is None:
            return None

        if not isinstance(value, Dict):
            raise ValueConversionError(f"{field_path} expected to be a dict with __type_name and __value")

        __type_name = value.get("__type_name")
        __value = value.get("__value")

        if __type_name is None or __value is None:
            # try all the types to convert the value, if only one type can convert it, return the converted value
            try_results = []
            for t in self._types:
                try:
                    converted_value = t.convert(value, f"{field_path}.__value", strict=True)
                    try_results.append((t, converted_value))
                except ValueConversionError:
                    try_results.append((t, None))
                    continue
            
            successful_conversions = [res for res in try_results if res[1] is not None]
            if len(successful_conversions) == 1:
                logger.warning(f"{field_path} expected to have __type_name and __value, but got value: {value}, successfully converted it to {successful_conversions[0][0]}")
                return successful_conversions[0][1]
            raise ValueConversionError(f"{field_path} expected to have __type_name and __value")

        actual_type = None
        for t in self._types:
            if repr(t) == __type_name:
                actual_type = t
                break

        if not actual_type:
            raise ValueConversionError(f"{field_path} has invalid __type_name")

        return actual_type.convert(__value, f"{field_path}.__value", strict)
    
    def convert_strict(self, value, field_path: str):
        if value is None:
            return None

        if not isinstance(value, Dict):
            raise ValueConversionError(f"{field_path} expected to be a dict with __type_name and __value")

        __type_name = value.get("__type_name")
        __value = value.get("__value")

        if __type_name is None or __value is None:
            raise ValueConversionError(f"{field_path} expected to have __type_name and __value")

        actual_type = None
        for t in self._types:
            if repr(t) == __type_name:
                actual_type = t
                break

        if not actual_type:
            raise ValueConversionError(f"{field_path} has invalid __type_name")

        return actual_type.convert(__value, f"{field_path}.__value", strict=True)

    def __repr__(self):
        type_strs = [repr(t) for t in self._types]
        return f"Union[{', '.join(type_strs)}]"

class AnyType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['AnyType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'Any':
            return AnyType(parent_type)
        if isinstance(annotation, ast.Constant) and annotation.value == 'Any':
            return AnyType(parent_type)
        return None
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['AnyType']:
        if py_type is Any:
            logger.debug(f"AnyType.from_python_type: {py_type}")
            return AnyType(parent_type)
        return None

    def __init__(self, parent_type):
        Type.__init__(self, parent_type)

    def convert(self, value, field_path: str, strict=False):
        return value
    
    def __repr__(self):
        return "Any"
    
class LiteralType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site, parent_type) -> Optional['LiteralType']:
        values = None
        if not hasattr(annotation.slice, 'elts'):
            values = [annotation.slice.value]
        else:
            values = [elt.value for elt in annotation.slice.elts]
        
        if all(isinstance(v, (str, int, float, bool)) for v in values):
            return LiteralType(parent_type, values)
        return None
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['LiteralType']:
        origin = typing.get_origin(py_type)
        args = typing.get_args(py_type)
        if origin is Literal and all(isinstance(v, (str, int, float, bool)) for v in args):
            logger.debug(f"LiteralType.from_python_type: {py_type}")
            return LiteralType(parent_type, list(args))
        return None
    
    def __init__(self, parent_type, values: List[Union[str, int, float, bool]]):
        Type.__init__(self, parent_type)
        self._values = values

    def convert(self, value, field_path: str, strict=False):
        if value is None:
            return None

        if value not in self._values:
            raise ValueConversionError(f"{field_path} expected to be one of {self._values}, but got {value}")

        return value

    def __repr__(self):
        value_strs = [repr(v) for v in self._values]
        return f"Literal[{', '.join(value_strs)}]"
    
class AliasType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['AliasType']:
        logger.debug(f"AliasType.from_annotation: {ast.dump(annotation)}...")
        alias_name = annotation.id if isinstance(annotation, ast.Name) else annotation.value

        # alias can self reference, so we need to check parent_type chain first
        current = parent_type
        while current:
            if isinstance(current, AliasType) and current._name == alias_name:
                logger.debug(f"AliasType.from_annotation: {ast.dump(annotation)} is self-referencing")
                return current
            current = current._parent_type

        module = call_site.get_module()
        if not module or not hasattr(module, alias_name):
            # only find type alias in the module of the call site
            # actually this type alias may be imported from other modules by the module of the call site
            # but we don't handle this case for simplicity
            return None

        alias_type = AliasType(parent_type, alias_name, None)
        # we need to find the type alias definition by analyzing the source code of the module
        module_file_tree = call_site.get_module_file_tree()
        if not module_file_tree:
            # TODO in notebook environment, leave it for later
            return None
    
        # usually type alias is defined at module level, so we only analyze the top level statements
        # and its a Assign statement with a Name on the left hand side
        for node in module_file_tree.body:
            if isinstance(node, ast.Assign) and node.targets and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id == alias_name:
                    original_type = Type.from_annotation(node.value, call_site, alias_type)
                    if original_type:
                        alias_type._original_type = original_type
                        logger.debug(f"AliasType.from_annotation: {ast.dump(annotation)}")
                        return alias_type
        return None

    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['AliasType']:
        if not isinstance(py_type, str):
            return None
        
        alias_name = py_type
        # alias can self reference, so we need to check parent_type chain first
        current = parent_type
        while current:
            if isinstance(current, AliasType) and current._name == alias_name:
                logger.debug(f"AliasType.from_python_type: {py_type} is self-referencing")
                return current
            current = current._parent_type

        module = call_site.get_module()
        if not module or not hasattr(module, alias_name):
            # only find type alias in the module of the call site
            # actually this type alias may be imported from other modules by the module of the call site
            # but we don't handle this case for simplicity
            return None
        
        logger.debug(f"AliasType.from_python_type: {py_type}...")
        alias_type = AliasType(parent_type, alias_name, None)
        py_type = getattr(module, alias_name)
        original_type = Type.from_python_type(py_type, call_site, alias_type)
        if not original_type:
            return None

        logger.debug(f"AliasType.from_python_type: {py_type}")
        alias_type._original_type = original_type
        return alias_type

    def __init__(self, parent_type, name: str, original_type: Type):
        Type.__init__(self, parent_type)
        self._name = name
        self._original_type = original_type

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        return self._original_type.related_dataclass_sources(visited)
    
    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        result = {self._name: f"{self._name} = {repr(self._original_type)}"}
        result.update(self._original_type.type_alias_sources(visited))
        return result

    def convert(self, value, field_path: str, strict=False):
        return self._original_type.convert(value, field_path, strict)

    def __repr__(self):
        return self._name
    
class OptionalType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site, parent_type) -> Optional['OptionalType']:
        logger.debug(f"OptionalType.from_annotation: {ast.dump(annotation)}...")
        optional_type = OptionalType(parent_type, None)
        item_type = Type.from_annotation(annotation.slice, call_site, optional_type)
        if item_type:
            optional_type._item_type = item_type
            logger.debug(f"OptionalType.from_annotation: {ast.dump(annotation)}")
            return optional_type
        return None
    
    @classmethod
    def from_python_type(cls, py_type: Any, call_site, parent_type) -> Optional['OptionalType']:
        if isinstance(py_type, typing._UnionGenericAlias) and repr(py_type).startswith('typing.Optional'):
            # the internal representation of Optional[T] is Union[T, NoneType]
            logger.debug(f"OptionalType.from_python_type: {py_type}...")
            optional_type = OptionalType(parent_type, None)
            args = typing.get_args(py_type)
            if len(args) == 2 and type(None) in args:
                non_none_type = args[0] if args[1] is type(None) else args[1]
                item_type = Type.from_python_type(non_none_type, call_site, optional_type)
                if item_type:
                    optional_type._item_type = item_type
                    logger.debug(f"OptionalType.from_python_type: {py_type}")
                    return optional_type
                return None
        return None

    def __init__(self, parent_type, item_type: 'Type'):
        Type.__init__(self, parent_type)
        self._item_type = item_type

    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        return self._item_type.related_dataclass_sources(visited)
    
    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        if self in visited:
            return {}
        
        visited.add(self)
        return self._item_type.type_alias_sources(visited)

    def convert(self, value, field_path: str, strict=False):
        if value is None:
            return None
        
        return self._item_type.convert(value, field_path, strict)

    def __repr__(self):
        return f"Optional[{self._item_type}]"
