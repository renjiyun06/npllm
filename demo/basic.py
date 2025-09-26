import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

from typing import List, Union, Optional, Any, Tuple, Dict, Literal

from npllm.core.llm import LLM

async def f_int():
    pass

async def f_float():
    pass

async def f_bool():
    pass

async def f_str():
    pass

async def f_list():
    pass

async def f_tuple():
    pass

async def f_tuple_without_type_annotations():
    pass

async def f_dict():
    pass

async def f_union() -> Union[Union[int, str], str]:
    llm = LLM()
    return await llm.reason()

async def f_optional() -> Optional[int]:
    llm = LLM()
    return await llm.reason("Never return None")

async def f_any():
    pass

async def f_literal():
    pass

async def f_if_stmt():
    pass

async def f_while_stmt():
    pass

async def f_return_stmt() -> int:
    llm = LLM()
    return await llm.reason()

async def main():
    print(await f_union())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())