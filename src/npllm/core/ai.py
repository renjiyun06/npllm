import inspect
import asyncio
import os
from types import FrameType
from typing import Any, Callable

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
                if (
                    caller_frame.f_code.co_filename != __file__ and 
                    "src/npllm/__init__.py" not in caller_frame.f_code.co_filename and
                    asyncio_path not in caller_frame.f_code.co_filename
                ):
                    return caller_frame
                caller_frame = caller_frame.f_back
            raise RuntimeError("Cannot find caller frame outside LLM class")
        
        async def ai_method_handler(*args, **kwargs) -> Any:
            call_site = CallSite.of(caller_frame(), method_name, kwargs['__is_async__'], debug=True)
            return await self._call_site_executor.execute(call_site, args, kwargs)
        
        def ai_method_handler_sync(*args, **kwargs) -> Any:
            event_loop = asyncio._get_running_loop()
            if not event_loop:
                event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(event_loop)
            return event_loop.run_until_complete(ai_method_handler(*args, **kwargs))
            
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