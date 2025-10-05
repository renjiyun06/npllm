import ast
import typing
from typing import Optional, Set, List
from types import ModuleType

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext

class StrType(Type):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Name | ast.Constant,
        runtime_context: RuntimeContext,
        enclosing_type: Type
    ) -> Optional['StrType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'str':
            return StrType(enclosing_type)
        if isinstance(annotation, ast.Constant) and (annotation.value == 'str' or type(annotation.value) == str):
            return StrType(enclosing_type)
        return None
    
    def __init__(self, enclosing_type: Type):
        Type.__init__(self, enclosing_type)

    def runtime_type(self) -> typing.Type:
        return str

    def get_referenced_custom_classes(self, visited: Optional[Set['Type']]=None) -> List[typing.Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return []

    def get_dependent_modules(self, visited: Optional[Set['Type']]=None) -> Set[ModuleType]:
        if visited is None:
            visited = set()
        if self in visited:
            return set()
        visited.add(self)
        return set()

    def __str__(self):
        return "str"