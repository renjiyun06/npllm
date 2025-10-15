import ast
from typing import Optional, Dict, Set, List, Type, Union
from types import ModuleType

from npllm.core.annotated_type import AnnotatedType
from npllm.core.notebook import Cell
from npllm.core.types.str_type import StrType

import logging

logger = logging.getLogger(__name__)
    
class DictType(AnnotatedType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        semantic_call, 
        enclosing_type: Optional[AnnotatedType]=None
    ) -> Optional['DictType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or 
            annotation.value.id not in ['Dict', 'dict']
        ):
            return None
        
        logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}...")
        dict_type = DictType(semantic_call, enclosing_type=enclosing_type)
        key_type = AnnotatedType.from_annotation(annotation.slice.elts[0], semantic_call, dict_type)
        value_type = AnnotatedType.from_annotation(annotation.slice.elts[1], semantic_call, dict_type)
        if key_type and value_type:
            if not isinstance(key_type, StrType):
                raise RuntimeError(f"Only str key type is supported in Dict: {ast.unparse(annotation)}")
            dict_type._key_type = key_type
            dict_type._value_type = value_type
            logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}")
            return dict_type
        raise RuntimeError(f"Failed to parse dict type: {ast.unparse(annotation)}")

    def __init__(
        self,
        semantic_call,
        key_type: Optional[AnnotatedType]=None, 
        value_type: Optional[AnnotatedType]=None,
        enclosing_type: Optional[AnnotatedType]=None
    ):
        AnnotatedType.__init__(self, semantic_call, enclosing_type)
        self._key_type = key_type
        self._value_type = value_type

    def runtime_type(self) -> Type:
        return Dict[self._key_type.runtime_type(), self._value_type.runtime_type()]

    def get_referenced_custom_classes(self, visited: Optional[Set[AnnotatedType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        result.extend(self._key_type.get_referenced_custom_classes(visited))
        result.extend(self._value_type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set[AnnotatedType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        dependent_modules = {}
        dependent_modules.update(self._key_type.get_dependent_modules(visited))
        dependent_modules.update(self._value_type.get_dependent_modules(visited))
        return dependent_modules

    def __str__(self):
        return f"Dict[{self._key_type}, {self._value_type}]"