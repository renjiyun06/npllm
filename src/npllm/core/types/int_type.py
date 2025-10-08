import ast
from typing import Optional, Set, List, Type, Dict, Union
from types import ModuleType

from npllm.core.call_site_return_type import CallSiteReturnType
from npllm.core.notebook import Cell

class IntType(CallSiteReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Name | ast.Constant,
        call_site,
        enclosing_type: Optional[CallSiteReturnType]=None
    ) -> Optional['IntType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'int':
            return IntType(call_site, enclosing_type)
        if isinstance(annotation, ast.Constant) and (annotation.value == 'int' or type(annotation.value) == int):
            return IntType(call_site, enclosing_type)
        return None
    
    def __init__(self, call_site, enclosing_type: Optional[CallSiteReturnType]=None):
        CallSiteReturnType.__init__(self, call_site, enclosing_type)

    def runtime_type(self) -> Type:
        return int

    def get_referenced_custom_classes(self, visited: Optional[Set[CallSiteReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return []
    
    def get_dependent_modules(self, visited: Optional[Set[CallSiteReturnType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        return {}

    def __str__(self):
        return "int"