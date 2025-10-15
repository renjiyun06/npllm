import ast
from typing import Optional, List, Union, Set, Type, Dict
from types import ModuleType

from npllm.core.semantic_call_return_type import SemanticCallReturnType
from npllm.core.notebook import Cell

import logging

logger = logging.getLogger(__name__)

class UnionType(SemanticCallReturnType):
    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Subscript | ast.BinOp,
        semantic_call, 
        enclosing_type: Optional[SemanticCallReturnType]=None
    ) -> Optional['UnionType']:
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}...")
            left_type = SemanticCallReturnType.from_annotation(annotation.left, semantic_call, enclosing_type)
            right_type = SemanticCallReturnType.from_annotation(annotation.right, semantic_call, enclosing_type)
            if left_type and right_type:
                logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                return UnionType(semantic_call, types=[left_type, right_type], enclosing_type=enclosing_type)
            else:
                raise RuntimeError(f"Failed to parse union type: {ast.unparse(annotation)}")
        elif isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name) and annotation.value.id in ['Union', 'union']:
            logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}...")
            union_type = UnionType(semantic_call, enclosing_type=enclosing_type)
            if not hasattr(annotation.slice, 'elts'):
                type = SemanticCallReturnType.from_annotation(annotation.slice, semantic_call, union_type)
                if type:
                    union_type._types = [type]
                    logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                    return union_type
                raise RuntimeError(f"Failed to parse union type: {ast.unparse(annotation)}")
            else:
                types = []
                for elt in annotation.slice.elts:
                    type = SemanticCallReturnType.from_annotation(elt, semantic_call, union_type)
                    if type:
                        types.append(type)
                    else:
                        raise RuntimeError(f"Failed to parse union type: {ast.unparse(annotation)}")
                union_type._types = types
                logger.debug(f"UnionType.from_annotation: {ast.dump(annotation)}")
                return union_type
        else:
            return None
    
    def __init__(self, semantic_call, types: Optional[List[SemanticCallReturnType]]=None, enclosing_type: Optional[SemanticCallReturnType]=None):
        SemanticCallReturnType.__init__(self, semantic_call, enclosing_type)
        self._types = types

    def runtime_type(self) -> Type:
        types = [type.runtime_type() for type in self._types]
        return Union[*types]

    def get_referenced_custom_classes(self, visited: Optional[Set[SemanticCallReturnType]]=None) -> List[Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        for type in self._types:
            result.extend(type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set[SemanticCallReturnType]]=None) -> Dict[str, Union[ModuleType, Cell]]:
        if visited is None:
            visited = set()
        if self in visited:
            return {}
        visited.add(self)
        dependent_modules = {}
        for type in self._types:
            dependent_modules.update(type.get_dependent_modules(visited))
        return dependent_modules

    def __str__(self):
        return f"Union[{', '.join([str(type) for type in self._types])}]"