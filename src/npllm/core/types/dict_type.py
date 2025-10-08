import ast
from typing import Optional, Dict, Set, List, Type
from types import ModuleType

from npllm.core.call_site_return_type import CallSiteReturnType
from npllm.core.types.str_type import StrType

import logging

logger = logging.getLogger(__name__)
    
class DictType(CallSiteReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        call_site, 
        enclosing_type: Optional[CallSiteReturnType]=None
    ) -> Optional['DictType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or 
            annotation.value.id not in ['Dict', 'dict']
        ):
            return None
        
        logger.debug(f"DictType.from_annotation: {ast.dump(annotation)}...")
        dict_type = DictType(enclosing_type=enclosing_type)
        key_type = CallSiteReturnType.from_annotation(annotation.slice.elts[0], call_site, dict_type)
        value_type = CallSiteReturnType.from_annotation(annotation.slice.elts[1], call_site, dict_type)
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
        key_type: Optional[CallSiteReturnType]=None, 
        value_type: Optional[CallSiteReturnType]=None,
        enclosing_type: Optional[CallSiteReturnType]=None
    ):
        CallSiteReturnType.__init__(self, enclosing_type)
        self._key_type = key_type
        self._value_type = value_type

    def runtime_type(self) -> Type:
        return Dict[self._key_type.runtime_type(), self._value_type.runtime_type()]

    def get_referenced_custom_classes(self, visited: Optional[Set[CallSiteReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        result.extend(self._key_type.get_referenced_custom_classes(visited))
        result.extend(self._value_type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set[CallSiteReturnType]]=None) -> Set[ModuleType]:
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