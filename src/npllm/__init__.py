import builtins
import sys
import ast
import dataclasses
import inspect
from typing import Set

from IPython import get_ipython

from npllm.core.ai import AI
from npllm.core.execute_engines.agent.agent_execution_engine import AgentExecutionEngine

import logging

logger = logging.getLogger(__name__)

_ai = AI(semantic_execute_engine=AgentExecutionEngine())
_enabled = False

_excluded: Set[str] = {
    '__annotations__', '__builtins__', '__doc__', '__loader__',
    '__name__', '__package__', '__spec__',
    'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
    'type', 'object', 'Exception', 'print', 'len', 'range'
}

_ai_base_excluded_classes_by_module = {}

def _enable_module_ai():
    global _ai, _excluded

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
    excluded_class_names: Set[str] = set()
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

        if isinstance(n, ast.ClassDef):
            is_dataclass_decorated = False
            for deco in n.decorator_list:
                target = deco.func if isinstance(deco, ast.Call) else deco
                if isinstance(target, ast.Name) and target.id == 'dataclass':
                    is_dataclass_decorated = True
                    break
                if isinstance(target, ast.Attribute) and target.attr == 'dataclass':
                    is_dataclass_decorated = True
                    break
            if is_dataclass_decorated:
                excluded_class_names.add(n.name)
                continue

            is_pydantic_like = False
            for b in n.bases:
                if isinstance(b, ast.Name) and b.id == 'BaseModel':
                    is_pydantic_like = True
                    break
                if isinstance(b, ast.Attribute) and b.attr == 'BaseModel':
                    is_pydantic_like = True
                    break
            if is_pydantic_like:
                excluded_class_names.add(n.name)

    logger.info(f"Injecting {to_inject} into {mod_globals}")

    for name in to_inject:
        mod_globals.setdefault(name, getattr(_ai, name))

    mod_name = mod_globals.get('__name__')
    if mod_name:
        _ai_base_excluded_classes_by_module.setdefault(mod_name, set()).update(excluded_class_names)

class AIBase(AI):
    def __init__(self):
        AI.__init__(self, semantic_execute_engine=AgentExecutionEngine())

_ai_base_target_modules: Set[str] = set()
_ai_base_original_build_class = None

def _find_target_module_name_and_globals():
    frame = inspect.currentframe()
    if frame:
        frame = frame.f_back

    candidates = []
    while frame:
        try:
            name = frame.f_globals.get('__name__')
        except Exception:
            name = None
        filename = frame.f_code.co_filename

        if __file__ in filename:
            frame = frame.f_back
            continue
        if name and not name.startswith('importlib') and not name.startswith('npllm'):
            candidates.append(frame)
        frame = frame.f_back

    target_frame = None
    if candidates:
        target_frame = next((f for f in candidates if f.f_globals.get('__name__') == '__main__'), candidates[0])

    if target_frame:
        mod_globals = target_frame.f_globals
        mod_name = mod_globals.get('__name__')
        if mod_name:
            return mod_name, mod_globals

    if '__main__' in sys.modules:
        try:
            return '__main__', sys.modules['__main__'].__dict__
        except Exception:
            return '__main__', None

    return None, None

def _ensure_ai_initialized_on_class(cls_obj):
    orig_init = getattr(cls_obj, '__init__', None)

    def wrapped_init(self, *a, **kw):
        if orig_init is not None:
            orig_init(self, *a, **kw)
        
        AIBase.__init__(self)

    try:
        wrapped_init.__name__ = getattr(orig_init, '__name__', '__init__')
        wrapped_init.__qualname__ = getattr(orig_init, '__qualname__', wrapped_init.__qualname__)
    except Exception:
        pass
    setattr(cls_obj, '__init__', wrapped_init)

def _is_pydantic_base_class(t):
    try:
        for m in getattr(t, '__mro__', ()):
            if getattr(m, '__name__', '') == 'BaseModel' and 'pydantic' in getattr(m, '__module__', ''):
                return True
    except Exception:
        pass
    return False

def _enable_ai_base_inject():
    global _ai_base_target_modules, _ai_base_original_build_class

    mod_name, _ = _find_target_module_name_and_globals()
    if mod_name:
        _ai_base_target_modules.add(mod_name)

    _ai_base_original_build_class = builtins.__build_class__

    def _patched_build_class(func, name, *bases, **kwargs):
        cls = _ai_base_original_build_class(func, name, *bases, **kwargs)

        try:
            defining_mod = func.__globals__.get('__name__')
        except Exception:
            defining_mod = None

        if defining_mod in _ai_base_target_modules and defining_mod != __name__:
            try:
                if dataclasses.is_dataclass(cls):
                    return cls
            except Exception:
                pass

            try:
                if any(_is_pydantic_base_class(b) for b in cls.__bases__):
                    return cls
            except Exception:
                pass

            try:
                excluded = _ai_base_excluded_classes_by_module.get(defining_mod)
                if excluded and name in excluded:
                    return cls
            except Exception:
                pass

            if AIBase not in cls.__mro__:
                try:
                    new_bases = (AIBase,) + tuple(b for b in cls.__bases__ if b is not AIBase)
                    cls.__bases__ = new_bases
                    _ensure_ai_initialized_on_class(cls)
                except TypeError as e:
                    try:
                        namespace = {}
                        for k, v in cls.__dict__.items():
                            if k in ('__dict__', '__weakref__', '__slots__'):
                                continue
                            namespace[k] = v
                        namespace.setdefault('__module__', defining_mod)
                        namespace.setdefault('__qualname__', name)
                        new_bases = (AIBase,) + tuple(b for b in cls.__bases__ if b is not AIBase)
                        new_cls = type(name, new_bases, namespace)
                        _ensure_ai_initialized_on_class(new_cls)
                        try:
                            func.__globals__[name] = new_cls
                        except Exception:
                            pass
                        cls = new_cls
                    except Exception as e2:
                        pass
        return cls

    builtins.__build_class__ = _patched_build_class

def _enable_python_ai():
    global _enabled
    _enable_module_ai()
    _enable_ai_base_inject()
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
