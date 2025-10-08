import ast

from npllm.core.call_site_ctx import CallSiteCtx
from npllm.core.call_site_return_type import CallSiteReturnType

class AnnAssignCtx(CallSiteCtx):
    def __init__(self, call_site, ann_assign: ast.AnnAssign):
        CallSiteCtx.__init__(self, call_site)
        self._ann_assign = ann_assign
        self._return_type = self._parse_return_type()

    def _parse_return_type(self) -> CallSiteReturnType:
        type = CallSiteReturnType.from_annotation(self._ann_assign.annotation, self._call_site)
        if type:
            return type

        raise RuntimeError(f"Failed to parse return type for {self._call_site}")

    @property
    def return_type(self) -> CallSiteReturnType:
        return self._return_type