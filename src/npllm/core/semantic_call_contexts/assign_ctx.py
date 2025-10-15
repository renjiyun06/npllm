import ast

from npllm.core.semantic_call_ctx import SemanticCallCtx
from npllm.core.annotated_type import AnnotatedType

import logging

logger = logging.getLogger(__name__)

class AssignCtx(SemanticCallCtx):
    def __init__(self, semantic_call, assign: ast.Assign):
        SemanticCallCtx.__init__(self, semantic_call)
        self._assign = assign
        self._return_type = self._parse_return_type()
    
    def _parse_return_type(self) -> AnnotatedType:
        kwargs = {kw.arg: kw.value for kw in self._semantic_call._node.keywords}
        if "return_type" in kwargs:
            return AnnotatedType.from_annotation(kwargs["return_type"], self._semantic_call)
        
        target = self._assign.targets[0]
        if isinstance(target, ast.Tuple):
            # a, b = generate(...) is not supported yet
            raise RuntimeError(f"Tuple assignment is not supported yet at {self._semantic_call}")
        
        var_name = None
        if isinstance(target, ast.Attribute) and target.value.id == 'self':
            var_name = f"self.{target.attr}"
        elif isinstance(target, ast.Name):
            var_name = target.id

        if not var_name:
            # we only support assignment to self.var_name or var_name
            raise RuntimeError(f"Unsupported assignment: {ast.unparse(self._assign)} at {self._semantic_call}")

        declaration_node = self._semantic_call.get_annotated_declaration_node(var_name)
        if not declaration_node:
            raise RuntimeError(f"Cannot get annotated declaration node for variable {var_name} at {self._semantic_call}")
        
        type = AnnotatedType.from_annotation(declaration_node.annotation, self._semantic_call)
        if type:
            return type

        raise RuntimeError(f"Failed to parse return type for {self._semantic_call}")

    @property
    def return_type(self) -> AnnotatedType:
        return self._return_type