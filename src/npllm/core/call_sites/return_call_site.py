import ast
from typing import Union, Optional

from npllm.core.call_site import CallSite
from npllm.core.type import Type
from npllm.core.types.any_type import AnyType

class ReturnCallSite(CallSite):
    def parse_return_type(self) -> Type:
        enclosing_function_def: Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]] = self._get_enclosing_function_def()
        if not enclosing_function_def:
            raise RuntimeError(f"Cannot find enclosing function for return statement at call site {self}")
        
        if not enclosing_function_def.returns:
            raise RuntimeError(f"Cannot parse return type at call site {self} because the enclosing function {enclosing_function_def.name} has no return type")
        
        type = Type.from_annotation(enclosing_function_def.returns, self)
        if type:
            return type
        
        raise RuntimeError(f"Cannot parse return type at call site {self}")