import ast
from typing import Optional, List, Set, Type, Dict, Union
from types import ModuleType

from npllm.core.call_site_return_type import CallSiteReturnType
from npllm.core.notebook import Cell

import logging

logger = logging.getLogger(__name__)

class ListType(CallSiteReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript, 
        call_site, 
        enclosing_type: Optional[CallSiteReturnType]=None
    ) -> Optional['ListType']:
        if (
            not isinstance(annotation, ast.Subscript) or 
            not isinstance(annotation.value, ast.Name) or
            annotation.value.id not in ['List', 'list']
        ):
            return None
        
        logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}...")
        list_type = ListType(call_site, enclosing_type=enclosing_type)
        item_type = CallSiteReturnType.from_annotation(annotation.slice, call_site, list_type)
        if item_type:
            list_type._item_type = item_type
            logger.debug(f"ListType.from_annotation: {ast.dump(annotation)}")
            return list_type

        raise RuntimeError(f"Failed to parse list type for {ast.dump(annotation)}")
        
    
    def __init__(self, call_site, item_type: Optional[CallSiteReturnType]=None, enclosing_type: Optional[CallSiteReturnType]=None):
        CallSiteReturnType.__init__(self, call_site, enclosing_type)
        self._item_type = item_type

    def runtime_type(self) -> Type:
        return List[self._item_type.runtime_type()]

    def get_referenced_custom_classes(self, visited: Optional[Set[CallSiteReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        return self._item_type.get_referenced_custom_classes(visited)

    def get_dependent_modules(self, visited: Optional[Set[CallSiteReturnType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        return self._item_type.get_dependent_modules(visited)

    def __str__(self):
        return f"List[{self._item_type}]"