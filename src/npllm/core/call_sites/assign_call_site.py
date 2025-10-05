import ast
import inspect
from typing import Tuple
from types import FrameType

from npllm.core.call_site import CallSite
from npllm.core.type import Type
from npllm.core.types.tuple_type import TupleType
from npllm.core.types.any_type import AnyType

import logging

logger = logging.getLogger(__name__)

class AssignCallSite(CallSite):
    def __init__(
        self,
        identifier: Tuple[str, int, str],
        caller_frame: FrameType,
        method_name: str,
        call_node: ast.Call,
        assign: ast.Assign
    ):
        self._assign = assign
        CallSite.__init__(self, identifier, caller_frame, method_name, call_node)
    
    def parse_return_type(self) -> Type:
        target = self._assign.targets[0]
        if isinstance(target, ast.Tuple):
            # elts_len = len(target.elts)
            # tuple_type = TupleType()
            # item_types = [AnyType(tuple_type) for _ in range(elts_len)]
            # tuple_type._item_types = item_types
            # return tuple_type
            # TODO
            raise RuntimeError(f"Unsupported assignment target type: {ast.dump(target)} at call site {self}")
        
        var_name = None
        if isinstance(target, ast.Attribute) and target.value.id == 'self':
            var_name = f"self.{target.attr}"
        elif isinstance(target, ast.Name):
            var_name = target.id

        if not var_name:
            # we only support assignment to self.var_name or var_name
            raise RuntimeError(f"Unsupported assignment target type: {ast.dump(target)} at call site {self}")

        declaration_node = self._find_annotated_declaration_node(var_name)
        if not declaration_node:
            raise RuntimeError(f"Cannot find declaration node for variable {var_name} at call site {self}")
        
        type = Type.from_annotation(declaration_node.annotation, self)
        if type:
            return type

        raise RuntimeError(f"Cannot parse return type at call site {self}")