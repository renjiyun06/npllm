import ast

from npllm.core.call_site_ctx import CallSiteCtx
from npllm.core.call_site_return_type import CallSiteReturnType

import logging

logger = logging.getLogger(__name__)

class AssignCtx(CallSiteCtx):
    def __init__(self, call_site, assign: ast.Assign):
        CallSiteCtx.__init__(self, call_site)
        self._assign = assign
        self._return_type = self._parse_return_type()
    
    def _parse_return_type(self) -> CallSiteReturnType:
        kwargs = {kw.arg: kw.value for kw in self._call_site._node.keywords}
        if "return_type" in kwargs:
            return CallSiteReturnType.from_annotation(kwargs["return_type"], self._call_site)
        
        target = self._assign.targets[0]
        if isinstance(target, ast.Tuple):
            # a, b = generate(...) is not supported yet
            raise RuntimeError(f"Tuple assignment is not supported yet at {self._call_site}")
        
        var_name = None
        if isinstance(target, ast.Attribute) and target.value.id == 'self':
            var_name = f"self.{target.attr}"
        elif isinstance(target, ast.Name):
            var_name = target.id

        if not var_name:
            # we only support assignment to self.var_name or var_name
            raise RuntimeError(f"Unsupported assignment: {ast.unparse(self._assign)} at {self._call_site}")

        declaration_node = self._call_site.get_annotated_declaration_node(var_name)
        if not declaration_node:
            raise RuntimeError(f"Cannot get annotated declaration node for variable {var_name} at {self._call_site}")
        
        type = CallSiteReturnType.from_annotation(declaration_node.annotation, self._call_site)
        if type:
            return type

        raise RuntimeError(f"Failed to parse return type for {self._call_site}")

    @property
    def return_type(self) -> CallSiteReturnType:
        return self._return_type