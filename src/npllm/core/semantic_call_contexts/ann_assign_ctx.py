import ast

from npllm.core.semantic_call_ctx import SemanticCallCtx
from npllm.core.annotated_type import AnnotatedType

class AnnAssignCtx(SemanticCallCtx):
    def __init__(self, semantic_call, ann_assign: ast.AnnAssign):
        SemanticCallCtx.__init__(self, semantic_call)
        self._ann_assign = ann_assign
        self._return_type = self._parse_return_type()

    def _parse_return_type(self) -> AnnotatedType:
        type = AnnotatedType.from_annotation(self._ann_assign.annotation, self._semantic_call)
        if type:
            return type

        raise RuntimeError(f"Failed to parse return type for {self._semantic_call}")

    @property
    def return_type(self) -> AnnotatedType:
        return self._return_type