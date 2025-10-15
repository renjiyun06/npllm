import ast
from typing import Optional, List, Set, Type, Dict, Union
from types import ModuleType

from npllm.core.annotated_type import AnnotatedType
from npllm.core.notebook import Cell

import logging

logger = logging.getLogger(__name__)

class ListType(AnnotatedType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        semantic_call, 
        enclosing_type: Optional[AnnotatedType]=None
    ) -> Optional['ListType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or
            annotation.value.id not in ['List', 'list']
        ):
            return None
        
        logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}...")
        list_type = ListType(semantic_call, enclosing_type=enclosing_type)
        item_type = AnnotatedType.from_annotation(annotation.slice, semantic_call, list_type)
        if item_type:
            list_type._item_type = item_type
            logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}")
            return list_type

        raise RuntimeError(f"Failed to parse list type: {ast.unparse(annotation)}")
        
    
    def __init__(self, semantic_call, item_type: Optional[AnnotatedType]=None, enclosing_type: Optional[AnnotatedType]=None):
        AnnotatedType.__init__(self, semantic_call, enclosing_type)
        self._item_type = item_type

    def runtime_type(self) -> Type:
        return List[self._item_type.runtime_type()]

    def get_referenced_custom_classes(self, visited: Optional[Set[AnnotatedType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return self._item_type.get_referenced_custom_classes(visited)

    def get_dependent_modules(self, visited: Optional[Set[AnnotatedType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        return self._item_type.get_dependent_modules(visited)

    def __str__(self):
        return f"List[{self._item_type}]"