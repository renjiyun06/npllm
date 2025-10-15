from abc import ABC, abstractmethod

from npllm.core.annotated_type import AnnotatedType

class SemanticCallCtx(ABC):
    def __init__(self, semantic_call):
        self._semantic_call = semantic_call

    @abstractmethod
    def return_type(self) -> AnnotatedType:
        pass