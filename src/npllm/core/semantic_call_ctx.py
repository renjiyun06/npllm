from abc import ABC, abstractmethod

from npllm.core.call_site_return_type import CallSiteReturnType

class CallSiteCtx(ABC):
    def __init__(self, call_site):
        self._call_site = call_site

    @abstractmethod
    def return_type(self) -> CallSiteReturnType:
        pass