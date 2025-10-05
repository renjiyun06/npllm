import ast
import typing
from typing import Optional, Dict, Set, List
from types import ModuleType

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext
from npllm.core.types.str_type import StrType

import logging

logger = logging.getLogger(__name__)
    

class DictType(Type):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        runtime_context: RuntimeContext, 
        enclosing_type: Type
    ) -> Optional['DictType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or 
            annotation.value.id not in ['Dict', 'dict']
        ):
            return None
        
        logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}...")
        dict_type = DictType(enclosing_type)
        key_type = Type.from_annotation(annotation.slice.elts[0], runtime_context, dict_type)
        value_type = Type.from_annotation(annotation.slice.elts[1], runtime_context, dict_type)
        if key_type and value_type:
            if not isinstance(key_type, StrType):
                raise RuntimeError("Only str key type is supported in Dict")
            dict_type._key_type = key_type
            dict_type._value_type = value_type
            logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}")
            return dict_type
        raise RuntimeError(f"Failed to parse dict type for {ast.dump(annotation)}")

    def __init__(
        self, 
        enclosing_type: Type, 
        key_type: Optional[Type]=None, 
        value_type: Optional[Type]=None
    ):
        Type.__init__(self, enclosing_type)
        self._key_type = key_type
        self._value_type = value_type

    def runtime_type(self) -> typing.Type:
        return Dict[self._key_type.runtime_type(), self._value_type.runtime_type()]

    def get_referenced_custom_classes(self, visited: Optional[Set['Type']]=None) -> List[typing.Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        result.extend(self._key_type.get_referenced_custom_classes(visited))
        result.extend(self._value_type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set['Type']]=None) -> Set[ModuleType]:
        if visited is None:
            visited = set()
        if self in visited:
            return set()
        visited.add(self)
        dependent_modules = set()
        dependent_modules.update(self._key_type.get_dependent_modules(visited))
        dependent_modules.update(self._value_type.get_dependent_modules(visited))
        return dependent_modules

    def __str__(self):
        return f"Dict[{self._key_type}, {self._value_type}]"