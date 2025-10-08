import ast
from typing import Optional, List, Union, Set, Type
from types import ModuleType

from npllm.core.call_site_return_type import CallSiteReturnType

import logging

logger = logging.getLogger(__name__)

class UnionType(CallSiteReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript | ast.BinOp,
        call_site, 
        enclosing_type: Optional[CallSiteReturnType]=None
    ) -> Optional['UnionType']:
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}...")
            left_type = CallSiteReturnType.from_annotation(annotation.left, call_site, enclosing_type)
            right_type = CallSiteReturnType.from_annotation(annotation.right, call_site, enclosing_type)
            if left_type and right_type:
                logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                return UnionType(types=[left_type, right_type], enclosing_type=enclosing_type)
            else:
                raise RuntimeError(f"Failed to parse union type for {ast.dump(annotation)}")
        elif isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name) and annotation.value.id in ['Union', 'union']:
            logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}...")
            union_type = UnionType(enclosing_type=enclosing_type)
            if not hasattr(annotation.slice, 'elts'):
                type = CallSiteReturnType.from_annotation(annotation.slice, call_site, union_type)
                if type:
                    union_type._types = [type]
                    logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                    return union_type
                raise RuntimeError(f"Failed to parse union type for {ast.dump(annotation)}")
            else:
                types = []
                for elt in annotation.slice.elts:
                    type = CallSiteReturnType.from_annotation(elt, call_site, union_type)
                    if type:
                        types.append(type)
                    else:
                        raise RuntimeError(f"Failed to parse union type for {ast.dump(annotation)}")
                union_type._types = types
                logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                return union_type
        else:
            return None
    
    def __init__(self, types: Optional[List[CallSiteReturnType]]=None, enclosing_type: Optional[CallSiteReturnType]=None):
        CallSiteReturnType.__init__(self, enclosing_type)
        self._types = types

    def runtime_type(self) -> Type:
        types = [type.runtime_type() for type in self._types]
        return Union[*types]

    def get_referenced_custom_classes(self, visited: Optional[Set[CallSiteReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        for type in self._types:
            result.extend(type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set[CallSiteReturnType]]=None) -> Set[ModuleType]:
        if visited is None:
            visited = set()
        if self in visited:
            return set()
        visited.add(self)
        dependent_modules = set()
        for type in self._types:
            dependent_modules.update(type.get_dependent_modules(visited))
        return dependent_modules

    def __str__(self):
        return f"Union[{', '.join([str(type) for type in self._types])}]"