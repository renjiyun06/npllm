from npllm.core.semantic_call_ctx import SemanticCallCtx
from npllm.core.annotated_type import AnnotatedType

class ReturnCtx(SemanticCallCtx):
    def __init__(self, semantic_call):
        SemanticCallCtx.__init__(self, semantic_call)
        self._return_type = self._parse_return_type()

    def _parse_return_type(self) -> AnnotatedType:
        enclosing_function_def = self._semantic_call.enclosing_function_def
        assert enclosing_function_def
        
        if not enclosing_function_def.returns:
            raise RuntimeError(f"Cannot parse return type for {self._semantic_call} because the enclosing function {enclosing_function_def.name} has no return statement")
        
        type = AnnotatedType.from_annotation(enclosing_function_def.returns, self._semantic_call)
        if type:
            return type
        
        raise RuntimeError(f"Failed to parse return type for {self._semantic_call}")

    @property
    def return_type(self) -> AnnotatedType:
        return self._return_type