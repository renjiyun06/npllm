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
        x: int -> IntType("int")
        y: List[int] -> ListType(IntType("int"))
        """
        result = None
        if isinstance(annotation, ast.Name) or isinstance(annotation, ast.Constant):
            result = (
                StrType.from_annotation(annotation, call_site, parent_type) or
                IntType.from_annotation(annotation, call_site, parent_type) or
                FloatType.from_annotation(annotation, call_site, parent_type) or
                BoolType.from_annotation(annotation, call_site, parent_type) or
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
    
    def __init__(self, parent_type):
        self._parent_type = parent_type
    
    def related_dataclass_sources(self, visited=set()) -> Dict[str, str]:
        return {}

    def type_alias_sources(self, visited=set()) -> Dict[str, str]:
        return {}

    @abstractmethod
    def __repr__(self):
        pass

class StrType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['StrType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'str':
            return StrType(parent_type)
        if isinstance(annotation, ast.Constant) and annotation.value == 'str':
            return StrType(parent_type)
        return None
    
    def __init__(self, parent_type):
        Type.__init__(self, parent_type)

    def __repr__(self):
        return "str"

    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "str"
        return isinstance(other, StrType)

class IntType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['IntType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'int':
            return IntType(parent_type)
        if isinstance(annotation, ast.Constant) and annotation.value == 'int':
            return IntType(parent_type)
        return None
    
    def __init__(self, parent_type):
        Type.__init__(self, parent_type)

    def __repr__(self):
        return "int"

    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "int"
        return isinstance(other, IntType)
    
class FloatType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['FloatType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'float':
            return FloatType(parent_type)
        if isinstance(annotation, ast.Constant) and annotation.value == 'float':
            return FloatType(parent_type)
        return None
    
    def __init__(self, parent_type):
        Type.__init__(self, parent_type)

    def __repr__(self):
        return "float"

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if isinstance(other, str):
            return other == "float"
        return isinstance(other, FloatType)
    
class BoolType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['BoolType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'bool':
            return BoolType(parent_type)
        if isinstance(annotation, ast.Constant) and annotation.value == 'bool':
            return BoolType(parent_type)
        return None
    
    def __init__(self, parent_type):
        Type.__init__(self, parent_type)

    def __repr__(self):
        return "bool"

    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "bool"
        return isinstance(other, BoolType)
    
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
    
    def __init__(self, parent_type, item_type: 'Type'):
        Type.__init__(self, parent_type)
        self._item_type = item_type

    @property
    def item_type(self):
        return self._item_type

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

    def __repr__(self):
        return f"List[{self._item_type}]"
    
    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "List"
        
        if not isinstance(other, ListType):
            return False
    
        return self._item_type == other._item_type
    
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

    def __init__(self, parent_type, item_types: tuple['Type', ...]):
        Type.__init__(self, parent_type)
        self._item_types = item_types

    @property
    def item_types(self):
        return self._item_types

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

    def __repr__(self):
        items_repr = []
        for item in self._item_types:
            items_repr.append(repr(item))
        return f"Tuple[{', '.join(items_repr)}]"
    
    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Tuple"
        
        if not isinstance(other, TupleType):
            return False
        
        if len(self._item_types) != len(other._item_types):
            return False
        
        return all(s == o for s, o in zip(self._item_types, other._item_types))

class DictType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Subscript, call_site, parent_type) -> Optional['DictType']:
        logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}...")
        dict_type = DictType(parent_type, None, None)
        key_type = Type.from_annotation(annotation.slice.elts[0], call_site, dict_type)
        value_type = Type.from_annotation(annotation.slice.elts[1], call_site, dict_type)
        if key_type and value_type:
            if not isinstance(key_type, StrType):
                raise RuntimeError("Only str key type is supported in Dict")
            dict_type._key_type = key_type
            dict_type._value_type = value_type
            logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}")
            return dict_type
        return None

    def __init__(self, parent_type, key_type: 'Type', value_type: 'Type'):
        Type.__init__(self, parent_type)
        self._key_type = key_type
        self._value_type = value_type

    @property
    def key_type(self):
        return self._key_type

    @property
    def value_type(self):
        return self._value_type

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

    def __repr__(self):
        return f"Dict[{self._key_type}, {self._value_type}]"
    
    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Dict"
        
        if not isinstance(other, DictType):
            return False
        
        return self._key_type == other._key_type and self._value_type == other._value_type

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

    def __init__(self, parent_type, dataclass_cls, field_types: Dict[str, 'Type'], call_site):
        Type.__init__(self, parent_type)
        self._dataclass_cls: typing.Type = dataclass_cls
        self._field_types = field_types
        self._call_site = call_site

    @property
    def dataclass_cls(self):
        return self._dataclass_cls

    @property
    def field_types(self):
        return self._field_types

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

    def __repr__(self):
        return f"{self._dataclass_cls.__name__}"
    
    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "dataclass"

        if not isinstance(other, DataclassType):
            return False
        
        if self._dataclass_cls != other._dataclass_cls:
            return False

        if len(self._field_types) != len(other._field_types):
            return False
        
        for key in self._field_types:
            if key not in other._field_types or self._field_types[key] != other._field_types[key]:
                return False

        return True

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
    
    def __init__(self, parent_type, types: List['Type']):
        Type.__init__(self, parent_type)
        self._types = types

    @property
    def types(self):
        return self._types

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

    def __repr__(self):
        type_strs = [repr(t) for t in self._types]
        return f"Union[{', '.join(type_strs)}]"

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Union"
    
        if not isinstance(other, UnionType):
            return False
        
        if len(self._types) != len(other._types):
            return False
        
        return all(s == o for s, o in zip(self._types, other._types))

class AnyType(Type):
    @classmethod
    def from_annotation(cls, annotation: ast.Name | ast.Constant, call_site, parent_type) -> Optional['AnyType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'Any':
            return AnyType(parent_type)
        if isinstance(annotation, ast.Constant) and annotation.value == 'Any':
            return AnyType(parent_type)
        return None
    
    def __init__(self, parent_type):
        Type.__init__(self, parent_type)
    
    def __repr__(self):
        return "Any"
    
    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Any"
        return isinstance(other, AnyType)

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
    
    def __init__(self, parent_type, values: List[Union[str, int, float, bool]]):
        Type.__init__(self, parent_type)
        self._values = values

    @property
    def values(self):
        return self._values

    def __repr__(self):
        value_strs = [repr(v) for v in self._values]
        return f"Literal[{', '.join(value_strs)}]"

    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Literal"
        
        if not isinstance(other, LiteralType):
            return False
        
        if len(self._values) != len(other._values):
            return False
        
        return all(s == o for s, o in zip(self._values, other._values))
    
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

    def __init__(self, parent_type, name: str, original_type: Type):
        Type.__init__(self, parent_type)
        # alias name
        self._name = name
        self._original_type = original_type

    @property
    def original_type(self):
        return self._original_type

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

    def __repr__(self):
        return self._name
    
    def __hash__(self):
        return super().__hash__()
    
    def __eq__(self, other):
        if isinstance(other, str):
            return other == "alias"
        
        if not isinstance(other, AliasType):
            return False
        
        return self._name == other._name and self._original_type == other._original_type
    
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

    def __init__(self, parent_type, item_type: 'Type'):
        Type.__init__(self, parent_type)
        self._item_type = item_type

    @property
    def item_type(self):
        return self._item_type

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

    def __repr__(self):
        return f"Optional[{self._item_type}]"

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Optional"
        
        if not isinstance(other, OptionalType):
            return False
        
        return self._item_type == other._item_type
