import asyncio
from typing import Callable

def dual_callable(async_func) -> Callable:
    class DualCallable:
        def __init__(self, async_func):
            self.async_func = async_func

        def __call__(self, *args, **kwargs):
            if asyncio._get_running_loop():
                return self.async_func(*args, **kwargs)
            else:
                return asyncio.run(self.async_func(*args, **kwargs))

    return DualCallable(async_func)