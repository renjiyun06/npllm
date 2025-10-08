from npllm.core.call_site_ctx import CallSiteCtx
from npllm.core.types.bool_type import BoolType

class WhileCtx(CallSiteCtx):
    def __init__(self, call_site):
        CallSiteCtx.__init__(self, call_site)
        self._return_type = BoolType()

    @property
    def return_type(self) -> BoolType:
        return self._return_type