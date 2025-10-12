import inspect
import asyncio
import os
import sys
from types import FrameType
from typing import Any, Callable
import builtins

from IPython import get_ipython

from npllm.core.call_site import CallSite
from npllm.core.call_site_executor import CallSiteExecutor

import logging

logger = logging.getLogger(__name__)

class AI:
    def __init__(self, call_site_executor: CallSiteExecutor=None):
        if call_site_executor is None:
            import npllm.agent.agent_executor
            call_site_executor = npllm.agent.agent_executor.AgentExecutor()

        self._call_site_executor = call_site_executor

    def __getattr__(self, method_name: str) -> Callable:

        def caller_frame() -> FrameType:
            caller_frame = inspect.currentframe()
            asyncio_path = os.path.dirname(asyncio.__file__)
            while caller_frame:
                if caller_frame.f_code.co_filename != __file__ and asyncio_path not in caller_frame.f_code.co_filename:
                    return caller_frame
                caller_frame = caller_frame.f_back
            raise RuntimeError("Cannot find caller frame outside LLM class")
        
        async def ai_method_handler(*args, **kwargs) -> Any:
            call_site = CallSite.of(caller_frame(), method_name, kwargs['__is_async__'], debug=True)
            return await self._call_site_executor.execute(call_site, args, kwargs)
        
        def ai_method_handler_sync(*args, **kwargs) -> Any:
            return asyncio.run(ai_method_handler(*args, **kwargs))
            
        class DualCallable:
            def __init__(self, async_func, sync_func):
                self.async_func = async_func
                self.sync_func = sync_func

            def __call__(self, *args, **kwargs):
                if asyncio._get_running_loop():
                    kwargs['__is_async__'] = True
                    return self.async_func(*args, **kwargs)
                else:
                    kwargs['__is_async__'] = False
                    return self.sync_func(*args, **kwargs)

        return DualCallable(ai_method_handler, ai_method_handler_sync)

_ai = AI()
_enabled = False
_original_ns = None

def _enable_python_ai():
    _enabled = True

def _enable_ipython_ai(ipython):
    global _ai, _enabled, _original_ns

    class InterceptingNamespace(dict):
        _excluded = {
            '__annotations__', '__builtins__', '__doc__', '__loader__', 
            '__name__', '__package__', '__spec__',
            'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
            'type', 'object', 'Exception', 'print', 'len', 'range'
        }

        def __missing__(self, key):
            if key.startswith('_'):
                raise KeyError(key)

            if key in InterceptingNamespace._excluded:
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

def disable_ai():
    global _enabled

    if not _enabled:
        return
    
    ipython = get_ipython()
    if ipython:
        ipython.user_ns = dict(ipython.user_ns)
        
        _enabled = False
    else:
        sys.settrace(None)
        _enabled = False

enable_ai()