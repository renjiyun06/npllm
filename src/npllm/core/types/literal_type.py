import ast
from typing import Optional, List, Union, Literal, Set, Type, Dict
from types import ModuleType

from npllm.core.semantic_call_return_type import SemanticCallReturnType

class LiteralType(SemanticCallReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript,
        semantic_call,
        enclosing_type: Optional[SemanticCallReturnType]=None
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
            return LiteralType(semantic_call, values, enclosing_type=enclosing_type)
        
        raise RuntimeError(f"Unsupported literal type: {ast.unparse(annotation)}")
    
    def __init__(self, semantic_call, values: List[Union[str, int, float, bool]], enclosing_type: Optional[SemanticCallReturnType]=None):
        SemanticCallReturnType.__init__(self, semantic_call, enclosing_type)
        self._values = values

    def runtime_type(self) -> Type:
        return Literal[self._values]

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
        return f"Literal[{', '.join(self._values)}]"