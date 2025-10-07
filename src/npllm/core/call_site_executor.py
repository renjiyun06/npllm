from abc import ABC, abstractmethod
from typing import Any, List, Dict

from npllm.core.call_site import CallSite

class CallSiteExecutor(ABC):
    @abstractmethod
    async def execute(self, call_site: CallSite, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        pass