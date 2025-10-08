import ast
from typing import Optional, Set, List, Type
from types import ModuleType

from npllm.core.call_site_return_type import CallSiteReturnType

class BoolType(CallSiteReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Name | ast.Constant,
        call_site,
        enclosing_type: Optional[CallSiteReturnType]=None
    ) -> Optional['BoolType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'bool':
            return BoolType(enclosing_type)
        if isinstance(annotation, ast.Constant) and (annotation.value == 'bool' or type(annotation.value) == bool):
            return BoolType(enclosing_type)
        return None
    
    def __init__(self, enclosing_type: Optional[CallSiteReturnType]=None):
        CallSiteReturnType.__init__(self, enclosing_type)

    def runtime_type(self) -> Type:
        return bool

    def get_referenced_custom_classes(self, visited: Optional[Set[CallSiteReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return []

    def get_dependent_modules(self, visited: Optional[Set[CallSiteReturnType]]=None) -> Set[ModuleType]:
        if visited is None:
            visited = set()
        if self in visited:
            return set()
        visited.add(self)
        return set()

    def __str__(self):
        return "bool"