import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

from dataclasses import dataclass
from typing import List, Dict

from npllm.core.llm import LLM

T = int | str

async def f_type_alias_1() -> T:
    llm = LLM()
    return await llm.reason()

async def f_type_alias_2() -> List[T]:
    llm = LLM()
    return await llm.reason()

async def f_type_alias_3() -> Dict[str, T]:
    llm = LLM()
    return await llm.reason()

async def f_type_alias_4() -> Dict[str, List[T]]:
    llm = LLM()
    return await llm.reason()

@dataclass
class Demo:
    a: int
    b: str
    c: List[T]

async def f_type_alias_5() -> Demo:
    llm = LLM()
    return await llm.reason()

async def main():
    print(await f_type_alias_1())
    print(await f_type_alias_2())
    print(await f_type_alias_3())
    print(await f_type_alias_4())
    print(await f_type_alias_5())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())