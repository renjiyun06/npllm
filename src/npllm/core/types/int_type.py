import ast
import typing
from typing import Optional, Set, List
from types import ModuleType

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext

class IntType(Type):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Name | ast.Constant,
        runtime_context: RuntimeContext,
        enclosing_type: Type
    ) -> Optional['IntType']:
        if isinstance(annotation, ast.Name) and annotation.id == 'int':
            return IntType(enclosing_type)
        if isinstance(annotation, ast.Constant) and (annotation.value == 'int' or type(annotation.value) == int):
            # TODO where does the int constant come from?
            return IntType(enclosing_type)
        return None
    
    def __init__(self, enclosing_type: Type):
        Type.__init__(self, enclosing_type)

    def runtime_type(self) -> typing.Type:
        return int

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
        return "int"