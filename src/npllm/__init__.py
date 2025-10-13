import builtins
import ast
import builtins
import inspect
from typing import Set

from IPython import get_ipython

from npllm.core.ai import AI

import logging

logger = logging.getLogger(__name__)

_ai = AI()
_enabled = False

_excluded: Set[str] = {
    '__annotations__', '__builtins__', '__doc__', '__loader__',
    '__name__', '__package__', '__spec__',
    'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
    'type', 'object', 'Exception', 'print', 'len', 'range'
}

def _enable_python_ai():
    global _ai, _enabled, _excluded
    
    caller_frame = inspect.currentframe()
    while caller_frame and (__file__ in caller_frame.f_code.co_filename or "importlib._bootstrap" in caller_frame.f_code.co_filename):
        caller_frame = caller_frame.f_back
        
    if not caller_frame:
        return

    mod_globals = caller_frame.f_globals
    filename = caller_frame.f_code.co_filename

    with open(filename, 'r', encoding='utf-8') as f:
        src = f.read()

    tree = ast.parse(src)

    defined: Set[str] = set(mod_globals.keys())

    def add_target_names(node):
        if isinstance(node, ast.Name):
            defined.add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                add_target_names(elt)

    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(n.name)
        elif isinstance(n, ast.Import):
            for alias in n.names:
                defined.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(n, ast.ImportFrom):
            for alias in n.names:
                defined.add(alias.asname or alias.name)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            defined.add(n.target.id)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                add_target_names(t)
        elif isinstance(n, ast.With):
            for item in n.items:
                if item.optional_vars:
                    add_target_names(item.optional_vars)

    to_inject: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            if name.startswith('_'):
                continue
            if name in defined or name in _excluded:
                continue
            if hasattr(builtins, name):
                continue
            to_inject.add(name)

    logger.info(f"Injecting {to_inject} into {mod_globals}")

    for name in to_inject:
        mod_globals.setdefault(name, getattr(_ai, name))

    _enabled = True

def _enable_ipython_ai(ipython):
    global _ai, _enabled, _excluded

    class InterceptingNamespace(dict):
        def __missing__(self, key):
            if key.startswith('_'):
                raise KeyError(key)

            if key in _excluded:
                raise KeyError(key)

            if hasattr(builtins, key):
                value = getattr(builtins, key)
                self[key] = value
                return value

            async def placeholder(*args, **kwargs):
                return await getattr(_ai, key)(*args, **kwargs)
            
            placeholder.__name__ = key
            self[key] = placeholder
            return placeholder

    _original_ns = ipython.user_ns
    ipython.user_ns = InterceptingNamespace(ipython.user_ns)
    
    _enabled = True

def enable_ai():
    if _enabled:
        return
    
    ipython = get_ipython()
    if ipython:
        _enable_ipython_ai(ipython)
    else:
        _enable_python_ai()

enable_ai()
