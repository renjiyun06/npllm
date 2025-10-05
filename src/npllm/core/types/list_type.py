import ast
import typing
from typing import Optional, List, Set
from types import ModuleType

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext

import logging

logger = logging.getLogger(__name__)

class ListType(Type):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        runtime_context: RuntimeContext, 
        enclosing_type: Type
    ) -> Optional['ListType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or
            annotation.value.id not in ['List', 'list']
        ):
            return None
        
        logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}...")
        list_type = ListType(enclosing_type)
        item_type = Type.from_annotation(annotation.slice, runtime_context, list_type)
        if item_type:
            list_type._item_type = item_type
            logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}")
            return list_type

        raise RuntimeError(f"Failed to parse list type for {ast.dump(annotation)}")
        
    
    def __init__(self, enclosing_type: Type, item_type: Optional[Type]=None):
        Type.__init__(self, enclosing_type)
        self._item_type = item_type

    def runtime_type(self) -> typing.Type:
        return List[self._item_type.runtime_type()]

    def get_referenced_custom_classes(self, visited: Optional[Set['Type']]=None) -> List[typing.Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return self._item_type.get_referenced_custom_classes(visited)

    def get_dependent_modules(self, visited: Optional[Set['Type']]=None) -> Set[ModuleType]:
        if visited is None:
            visited = set()
        if self in visited:
            return set()
        visited.add(self)
        return self._item_type.get_dependent_modules(visited)

    def __str__(self):
        return f"List[{self._item_type}]"