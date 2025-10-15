import ast
from typing import Optional, Set, List, Type, Dict, Union
from types import ModuleType

from npllm.core.semantic_call_return_type import SemanticCallReturnType
from npllm.core.notebook import Cell

class FloatType(SemanticCallReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Name | ast.Constant,
        semantic_call,
        enclosing_type: Optional[SemanticCallReturnType]=None
    ) -> Optional['FloatType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'float':
            return FloatType(semantic_call, enclosing_type)
        if isinstance(annotation, ast.Constant) and (annotation.value == 'float' or type(annotation.value) == float):
            return FloatType(semantic_call, enclosing_type)
        return None
    
    def __init__(self, semantic_call, enclosing_type: Optional[SemanticCallReturnType]=None):
        SemanticCallReturnType.__init__(self, semantic_call, enclosing_type)

    def runtime_type(self) -> Type:
        return float

    def get_referenced_custom_classes(self, visited: Optional[Set[SemanticCallReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return []

    def get_dependent_modules(self, visited: Optional[Set[SemanticCallReturnType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        return {}

    def __str__(self):
        return "float"