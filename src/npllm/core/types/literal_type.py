import ast
import typing
from typing import Optional, List, Union, Literal, Set
from types import ModuleType

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext

class LiteralType(Type):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript,
        runtime_context: RuntimeContext,
        enclosing_type: Type
    ) -> Optional['LiteralType']:

        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or 
            annotation.value.id not in ['Literal', 'literal']
        ):
            return None

        values = None
        if not hasattr(annotation.slice, 'elts'):
            values = [annotation.slice.value]
        else:
            values = [elt.value for elt in annotation.slice.elts]
        
        if all(isinstance(v, (str, int, float, bool)) for v in values):
            return LiteralType(enclosing_type, values)
        
        raise RuntimeError(f"Failed to parse literal type for {ast.dump(annotation)}")
    
    def __init__(self, enclosing_type: Type, values: List[Union[str, int, float, bool]]):
        Type.__init__(self, enclosing_type)
        self._values = values

    def runtime_type(self) -> typing.Type:
        return Literal[self._values]

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
        return f"Literal[{', '.join(self._values)}]"