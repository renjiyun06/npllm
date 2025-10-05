import ast
import typing
from typing import Optional, List, Tuple, Set
from types import ModuleType

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext

import logging

logger = logging.getLogger(__name__)

class TupleType(Type):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        runtime_context: RuntimeContext, 
        enclosing_type: Type
    ) -> Optional['TupleType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or 
            annotation.value.id not in ['Tuple', 'tuple']
        ):
            return None
        
        logger.debug(f"TupleType.from_annotation: {ast.dump(annotation)}...")
        tuple_type = TupleType(enclosing_type)
        item_types = []
        for elt in annotation.slice.elts:
            item_type = Type.from_annotation(elt, runtime_context, tuple_type)
            if item_type:
                item_types.append(item_type)
            else:
                raise RuntimeError(f"Failed to parse item type for {ast.dump(elt)}")
        
        tuple_type._item_types = item_types
        logger.debug(f"TupleType.from_annotation: {ast.dump(annotation)}")
        return tuple_type

    def __init__(self, enclosing_type: Optional[Type]=None, item_types: Optional[List[Type]]=None):
        Type.__init__(self, enclosing_type)
        self._item_types = item_types or []

    def runtime_type(self) -> typing.Type:
        item_types = [item_type.runtime_type() for item_type in self._item_types]
        return Tuple[*item_types]

    def get_referenced_custom_classes(self, visited: Optional[Set['Type']]=None) -> List[typing.Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        for item_type in self._item_types:
            result.extend(item_type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set['Type']]=None) -> Set[ModuleType]:
        if visited is None:
            visited = set()
        if self in visited:
            return set()
        visited.add(self)
        dependent_modules = set()
        for item_type in self._item_types:
            dependent_modules.update(item_type.get_dependent_modules(visited))
        return dependent_modules

    def __str__(self):
        return f"Tuple[{', '.join(self._item_types)}]"