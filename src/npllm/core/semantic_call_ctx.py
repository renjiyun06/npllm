from abc import ABC, abstractmethod

from npllm.core.semantic_call_return_type import SemanticCallReturnType

class SemanticCallCtx(ABC):
    def __init__(self, semantic_call):
        self._semantic_call = semantic_call

    @abstractmethod
    def return_type(self) -> SemanticCallReturnType:
        pass