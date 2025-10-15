from npllm.core.semantic_call_ctx import SemanticCallCtx
from npllm.core.types.bool_type import BoolType

class IfCtx(SemanticCallCtx):
    def __init__(self, semantic_call):
        SemanticCallCtx.__init__(self, semantic_call)
        self._return_type = BoolType()

    @property
    def return_type(self) -> BoolType:
        return self._return_type