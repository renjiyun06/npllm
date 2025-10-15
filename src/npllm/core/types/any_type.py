import ast
from typing import Optional, Any, Set, List, Type, Dict, Union
from types import ModuleType

from npllm.core.annotated_type import AnnotatedType
from npllm.core.notebook import Cell

class AnyType(AnnotatedType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Name | ast.Constant,
        semantic_call,
        enclosing_type: Optional[AnnotatedType]=None
    ) -> Optional['AnyType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'Any':
            return AnyType(semantic_call, enclosing_type)
        if isinstance(annotation, ast.Constant) and annotation.value == 'Any':
            return AnyType(semantic_call, enclosing_type)
        return None
    
    def __init__(self, semantic_call, enclosing_type: Optional[AnnotatedType]=None):
        AnnotatedType.__init__(self, semantic_call, enclosing_type)

    def runtime_type(self) -> Type:
        return Any

    def get_referenced_custom_classes(self, visited: Optional[Set[AnnotatedType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return []

    def get_dependent_modules(self, visited: Optional[Set[AnnotatedType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        return {}
    
    def __str__(self):
        return "Any"