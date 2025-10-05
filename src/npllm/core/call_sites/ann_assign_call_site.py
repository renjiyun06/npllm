import ast
import inspect
from typing import Tuple
from types import FrameType

from npllm.core.call_site import CallSite
from npllm.core.type import Type

class AnnAssignCallSite(CallSite):
    def __init__(
        self,
        identifier: Tuple[str, int, str],
        caller_frame: FrameType,
        method_name: str,
        call_node: ast.Call,
        ann_assign: ast.AnnAssign
    ):
        self._ann_assign = ann_assign
        CallSite.__init__(self, identifier, caller_frame, method_name, call_node)

    def parse_return_type(self) -> Type:
        type = Type.from_annotation(self._ann_assign.annotation, self)
        if type:
            return type

        raise RuntimeError(f"Cannot parse return type at call site {self}")