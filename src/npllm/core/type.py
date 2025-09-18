import inspect
from abc import ABC, abstractmethod
import typing
from typing import Literal, Dict, Union, List, Any, Optional, Tuple
import ast
from dataclasses import fields

from npllm.utils.notebook_util import get_dataclass_source

class ValueConversionError(Exception):
    pass

class Type(ABC):
    @classmethod
    def from_annotation(cls, annotation: ast.AST, call_site, parent_class=None) -> 'Type':
        """
        Create a Type instance from an AST annotation node

        Example:
        x: int -> BasicType("int")
        y: List[int] -> ListType(BasicType("int"))
        """
        result = None
        if isinstance(annotation, ast.Name):
            result = BasicType.from_annotation(annotation, call_site) or AnyType.from_annotation(annotation, call_site) or DataclassType.from_annotation(annotation, call_site, parent_class) 
        elif isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
            base_type = annotation.value.id
            if base_type == 'List' or base_type == 'list':
                result = ListType.from_annotation(annotation, call_site)
            elif base_type == 'Tuple' or base_type == 'tuple':
                result = TupleType.from_annotation(annotation, call_site)
            elif base_type == 'Dict' or base_type == 'dict':
                result = DictType.from_annotation(annotation, call_site)
            elif base_type == 'Union' or base_type == 'union':
                result = UnionType.from_annotation(annotation, call_site)
            elif base_type == 'Literal' or base_type == 'literal':
                result = LiteralType.from_annotation(annotation, call_site)
        elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            left_type = Type.from_annotation(annotation.left, call_site, parent_class)
            right_type = Type.from_annotation(annotation.right, call_site, parent_class)
            if left_type and right_type:
                result = UnionType([left_type, right_type])

        return result

    @abstractmethod
    def convert(self, value: Any, field_path: str=None):
        """
        Convert a JSON value to the target type value

        If conversion fails, raise ValueConversionError with a descriptive message which is llm friendly
        """
        pass

    def related_dataclass_sources(self) -> Dict[str, str]:
        return {}

    @abstractmethod
    def __repr__(self):
        pass

class BasicType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name, call_site) -> Optional['BasicType']:
        if annotation.id in ('str', 'int', 'float', 'bool'):
            return BasicType(annotation.id)
        return None
    
    def __init__(self, type: Literal["str", "int", "float", "bool"]):
        self._type = type

    def convert(self, value, field_path):
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

    def __repr__(self):
        return f"{self._type}"
    
class ListType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site) -> Optional['ListType']:
        item_type = Type.from_annotation(annotation.slice, call_site)
        if item_type:
            return ListType(item_type)
        return None

    def __init__(self, item_type: 'Type'):
        self._item_type = item_type

    def related_dataclass_sources(self) -> Dict[str, str]:
        return self._item_type.related_dataclass_sources()

    def convert(self, value, field_path: str):
        if value is None:
            return None
        
        if not isinstance(value, List):
            raise ValueConversionError(f"{field_path} expected to be a list")

        converted_list = []
        for i, item in enumerate(value):
            converted_item = self._item_type.convert(item, f"{field_path}[{i}]")
            converted_list.append(converted_item)
        return converted_list

    def __repr__(self):
        return f"List[{self._item_type}]"
    
class TupleType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site) -> Optional['TupleType']:
        item_types = []
        for elt in annotation.slice.elts:
            item_type = Type.from_annotation(elt, call_site)
            if item_type:
                item_types.append(item_type)
            else:
                return None
        return TupleType(tuple(item_types))

    def __init__(self, item_types: tuple['Type', ...]):
        self._item_types = item_types

    def related_dataclass_sources(self) -> Dict[str, str]:
        result = {}
        for item_type in self._item_types:
            result.update(item_type.related_dataclass_sources())
        return result
    
    def convert(self, value, field_path: str):
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValueConversionError(f"{field_path} expected to be a list")

        if len(self._item_types) != len(value):
            raise ValueConversionError(f"{field_path} expected to have {len(self._item_types)} items, but got {len(value)} items")

        converted_list = []
        for i, item_type in enumerate(self._item_types):
            converted_item = item_type.convert(value[i], f"{field_path}[{i}]")
            converted_list.append(converted_item)
        return tuple(converted_list)


    def __repr__(self):
        items_repr = []
        for item in self._item_types:
            items_repr.append(repr(item))
        return f"Tuple[{', '.join(items_repr)}]"

class DictType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site) -> Optional['DictType']:
        key_type = Type.from_annotation(annotation.slice.elts[0], call_site)
        value_type = Type.from_annotation(annotation.slice.elts[1], call_site)
        if key_type and value_type:
            if not isinstance(key_type, BasicType) or key_type._type != 'str':
                raise RuntimeError("Only str key type is supported in Dict")
            return DictType(key_type, value_type)
        return None

    def __init__(self, key_type: 'Type', value_type: 'Type'):
        self._key_type = key_type
        self._value_type = value_type

    def related_dataclass_sources(self) -> Dict[str, str]:
        result = {}
        result.update(self._key_type.related_dataclass_sources())
        result.update(self._value_type.related_dataclass_sources())
        return result
    
    def convert(self, value, field_path: str):
        if value is None:
            return None

        if not isinstance(value, Dict):
            raise ValueConversionError(f"{field_path} expected to be a dict")

        converted_dict = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueConversionError(f"{field_path} expected to have string keys, but got key of type {type(k).__name__}")
            converted_value = self._value_type.convert(v, f"{field_path}.{k}")
            converted_dict[k] = converted_value
        return converted_dict

    def __repr__(self):
        return f"Dict[{self._key_type}, {self._value_type}]"

class DataclassType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name, call_site, parent_class=None) -> Optional['DataclassType']:
        class_name = annotation.id
        dataclass_cls = call_site.get_dataclass(class_name, parent_class)
        if not dataclass_cls or not hasattr(dataclass_cls, '__dataclass_fields__'):
            return None
        field_types = {}
        for field in fields(dataclass_cls):
            field_types[field.name] = Type.from_annotation(ast.parse(field.type.__name__).body[0].value, call_site, parent_class=dataclass_cls)

        return DataclassType(dataclass_cls, field_types, call_site)

    def __init__(self, dataclass_cls, field_types: Dict[str, 'Type'], call_site):
        self._dataclass_cls: typing.Type = dataclass_cls
        self._field_types = field_types
        self._call_site = call_site

    def related_dataclass_sources(self) -> Dict[str, str]:
        result = {}
        if self._call_site.is_in_notebook():
            result[self._dataclass_cls.__qualname__] = get_dataclass_source(self._dataclass_cls)
        else:
            result[self._dataclass_cls.__qualname__] = inspect.getsource(self._dataclass_cls)

        for field_type in self._field_types.values():
            result.update(field_type.related_dataclass_sources())
        return result
    
    def convert(self, value, field_path: str):
        if value is None:
            return None
    
        if not isinstance(value, Dict):
            raise ValueConversionError(f"{field_path} expected to be a dict")
        
        field_values = {}
        for field_name, field_type in self._field_types.items():
            if field_name in value:
                field_value = field_type.convert(value[field_name], f"{field_path}.{field_name}")
                field_values[field_name] = field_value
            else:
                field_values[field_name] = None

        return self._dataclass_cls(**field_values)

    def __repr__(self):
        return f"{self._dataclass_cls.__name__}"

class UnionType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site) -> Optional['UnionType']:
        if not hasattr(annotation.slice, 'elts'):
            type = Type.from_annotation(annotation.slice)
            if type:
                return UnionType([type])
            return None
        
        types = []
        for elt in annotation.slice.elts:
            type = Type.from_annotation(elt, call_site)
            if type:
                types.append(type)
            else:
                return None
        return UnionType(types)
        
    def __init__(self, types: List['Type']):
        self._types = types

    def related_dataclass_sources(self) -> Dict[str, str]:
        result = {}
        for type in self._types:
            result.update(type.related_dataclass_sources())
        return result
    
    def convert(self, value, field_path: str):
        if value is None:
            return None

        if not isinstance(value, Dict):
            raise ValueConversionError(f"{field_path} expected to be a dict with __type_index, __type_name and __value")

        __type_index = value.get("__type_index")
        __type_name = value.get("__type_name")
        __value = value.get("__value")

        if __type_index is None or __type_name is None or __value is None:
            raise ValueConversionError(f"{field_path} expected to have __type_index, __type_name and __value")

        # check type index matches type name
        # if not match, use type name to find type
        actual_type = None
        if 0 <= __type_index < len(self._types):
            actual_type = self._types[__type_index]
            if repr(actual_type) != __type_name:
                for t in self._types:
                    if repr(t) == __type_name:
                        actual_type = t
                        break
        if not actual_type:
            raise ValueConversionError(f"{field_path} has invalid __type_index or __type_name")

        return actual_type.convert(__value, f"{field_path}.__value")

    def __repr__(self):
        type_strs = [repr(t) for t in self._types]
        return f"Union[{', '.join(type_strs)}]"

class AnyType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name, call_site) -> Optional['AnyType']:
        if annotation.id == 'Any':
            return AnyType()
        return None
    
    def convert(self, value, field_path: str):
        return value
    
    def __repr__(self):
        return "Any"
    
class LiteralType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site) -> Optional['LiteralType']:
        values = None
        if not hasattr(annotation.slice, 'elts'):
            values = [annotation.slice.value]
        else:
            values = [elt.value for elt in annotation.slice.elts]
        
        if all(isinstance(v, (str, int, float, bool)) for v in values):
            return LiteralType(values)
        return None
    
    def __init__(self, values: List[Union[str, int, float, bool]]):
        self._values = values

    def convert(self, value, field_path: str):
        if value is None:
            return None

        if value not in self._values:
            raise ValueConversionError(f"{field_path} expected to be one of {self._values}, but got {value}")

        return value

    def __repr__(self):
        value_strs = [repr(v) for v in self._values]
        return f"Literal[{', '.join(value_strs)}]"
