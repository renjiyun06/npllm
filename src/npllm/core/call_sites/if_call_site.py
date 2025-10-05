from npllm.core.call_site import CallSite
from npllm.core.types.bool_type import BoolType

class IfCallSite(CallSite):
    def parse_return_type(self) -> BoolType:
        return BoolType()