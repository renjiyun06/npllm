from npllm.core.call_site_ctx import CallSiteCtx
from npllm.core.call_site_return_type import CallSiteReturnType

class ReturnCtx(CallSiteCtx):
    def __init__(self, call_site):
        CallSiteCtx.__init__(self, call_site)
        self._return_type = self._parse_return_type()

    def _parse_return_type(self) -> CallSiteReturnType:
        enclosing_function_def = self._call_site.enclosing_function_def
        assert enclosing_function_def
        
        if not enclosing_function_def.returns:
            raise RuntimeError(f"Cannot parse return type for {self._call_site} because the enclosing function {enclosing_function_def.name} has no return statement")
        
        type = CallSiteReturnType.from_annotation(enclosing_function_def.returns, self._call_site)
        if type:
            return type
        
        raise RuntimeError(f"Failed to parse return type for {self._call_site}")

    @property
    def return_type(self) -> CallSiteReturnType:
        return self._return_type