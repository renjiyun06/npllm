import ast
from typing import Optional, Set, List, Type, Dict, Union
from types import ModuleType

from npllm.core.semantic_call_return_type import SemanticCallReturnType
from npllm.core.notebook import Cell

import logging

logger = logging.getLogger(__name__)

class OptionalType(SemanticCallReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        semantic_call, 
        enclosing_type: Optional[SemanticCallReturnType]=None
    ) -> Optional['OptionalType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or 
            annotation.value.id not in ['Optional', 'optional']
        ):
            return None
        
        logger.debug(f"OptionalType.from_annotation: {ast.dump(annotation)}...")
        optional_type = OptionalType(semantic_call, enclosing_type=enclosing_type)
        item_type = SemanticCallReturnType.from_annotation(annotation.slice, semantic_call, optional_type)
        if item_type:
            optional_type._item_type = item_type
            logger.debug(f"OptionalType.from_annotation: {ast.dump(annotation)}")
            return optional_type
        
        raise RuntimeError(f"Failed to parse optional type: {ast.unparse(annotation)}")

    def __init__(self, semantic_call, item_type: Optional[SemanticCallReturnType]=None, enclosing_type: Optional[SemanticCallReturnType]=None):
        SemanticCallReturnType.__init__(self, semantic_call, enclosing_type)
        self._item_type = item_type

    def runtime_type(self) -> Type:
        return Optional[self._item_type.runtime_type()]

    def get_referenced_custom_classes(self, visited: Optional[Set[SemanticCallReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return self._item_type.get_referenced_custom_classes(visited)

    def get_dependent_modules(self, visited: Optional[Set[SemanticCallReturnType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        return self._item_type.get_dependent_modules(visited)

    def __str__(self):
        return f"Optional[{self._item_type}]"