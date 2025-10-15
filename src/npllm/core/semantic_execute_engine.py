from abc import ABC, abstractmethod
from typing import Any, List, Dict

from npllm.core.semantic_call import SemanticCall

class SemanticExecuteEngine(ABC):
    @abstractmethod
    async def execute(self, semantic_call: SemanticCall, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        pass