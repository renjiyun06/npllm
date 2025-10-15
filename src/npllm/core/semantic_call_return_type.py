import ast
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Set, Dict, Union, Type
from types import ModuleType

from pydantic import TypeAdapter

from npllm.core.notebook import Cell

class SemanticCallReturnType(ABC):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.AST, 
        semantic_call, 
        enclosing_type: Optional['SemanticCallReturnType']=None
    ) -> 'SemanticCallReturnType':
        from npllm.core.types.str_type import StrType
        from npllm.core.types.int_type import IntType
        from npllm.core.types.float_type import FloatType
        from npllm.core.types.bool_type import BoolType
        from npllm.core.types.any_type import AnyType
        from npllm.core.types.custom_class_type import CustomClassType
        from npllm.core.types.list_type import ListType
        from npllm.core.types.tuple_type import TupleType
        from npllm.core.types.dict_type import DictType
        from npllm.core.types.union_type import UnionType
        from npllm.core.types.literal_type import LiteralType
        from npllm.core.types.optional_type import OptionalType
        
        return (
                StrType.from_annotation(annotation, semantic_call, enclosing_type) or
                IntType.from_annotation(annotation, semantic_call, enclosing_type) or
                FloatType.from_annotation(annotation, semantic_call, enclosing_type) or
                BoolType.from_annotation(annotation, semantic_call, enclosing_type) or
                AnyType.from_annotation(annotation, semantic_call, enclosing_type) or 
                ListType.from_annotation(annotation, semantic_call, enclosing_type) or
                TupleType.from_annotation(annotation, semantic_call, enclosing_type) or
                DictType.from_annotation(annotation, semantic_call, enclosing_type) or
                UnionType.from_annotation(annotation, semantic_call, enclosing_type) or
                LiteralType.from_annotation(annotation, semantic_call, enclosing_type) or
                OptionalType.from_annotation(annotation, semantic_call, enclosing_type) or 
                CustomClassType.from_annotation(annotation, semantic_call, enclosing_type)
            )
    
    def __init__(self, semantic_call, enclosing_type: Optional['SemanticCallReturnType']=None):
        self._semantic_call = semantic_call
        self._enclosing_type = enclosing_type

    def pydantic_type_adapter(self) -> TypeAdapter:
        return TypeAdapter(self.runtime_type())

    def json_schema(self) -> str:
        return json.dumps(self.pydantic_type_adapter().json_schema(), ensure_ascii=False, indent=2)

    @abstractmethod
    def runtime_type(self) -> Type:
        pass

    @abstractmethod
    def get_dependent_modules(self) -> Dict[str, Union[ModuleType, Cell]]:
        pass

    @abstractmethod
    def get_referenced_custom_classes(self, visited: Optional[Set[Type]]=None) -> List[Type]:
        pass

    @abstractmethod
    def __str__(self) -> str:
        pass