import ast
from typing import Optional, List, Tuple, Set, Type, Dict, Union
from types import ModuleType

from npllm.core.annotated_type import AnnotatedType
from npllm.core.notebook import Cell

import logging

logger = logging.getLogger(__name__)

class TupleType(AnnotatedType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        semantic_call, 
        enclosing_type: Optional[AnnotatedType]=None
    ) -> Optional['TupleType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or 
            annotation.value.id not in ['Tuple', 'tuple']
        ):
            return None
        
        logger.debug(f"TupleType.from_annotation: {ast.dump(annotation)}...")
        tuple_type = TupleType(semantic_call, enclosing_type=enclosing_type)
        item_types = []
        for elt in annotation.slice.elts:
            item_type = AnnotatedType.from_annotation(elt, semantic_call, tuple_type)
            if item_type:
                item_types.append(item_type)
            else:
                raise RuntimeError(f"Failed to parse item type: {ast.unparse(elt)}")
        
        tuple_type._item_types = item_types
        logger.debug(f"TupleType.from_annotation: {ast.dump(annotation)}")
        return tuple_type

    def __init__(self, semantic_call, enclosing_type: Optional[AnnotatedType]=None, item_types: Optional[List[AnnotatedType]]=None):
        AnnotatedType.__init__(self, semantic_call, enclosing_type)
        self._item_types = item_types or []

    def runtime_type(self) -> Type:
        item_types = [item_type.runtime_type() for item_type in self._item_types]
        return Tuple[*item_types]

    def get_referenced_custom_classes(self, visited: Optional[Set[AnnotatedType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        for item_type in self._item_types:
            result.extend(item_type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set[AnnotatedType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        dependent_modules = {}
        for item_type in self._item_types:
            dependent_modules.update(item_type.get_dependent_modules(visited))
        return dependent_modules

    def __str__(self):
        return f"Tuple[{', '.join([str(item_type) for item_type in self._item_types])}]"