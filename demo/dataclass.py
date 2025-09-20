import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

from dataclasses import dataclass
from typing import List, Dict, Optional

from npllm.core.llm import LLM

@dataclass
class Address:
    street: str
    city: str
    zip_code: str

@dataclass
class Person:
    name: str
    age: int
    address: Address

async def f_dataclass_1() -> Person:
    llm = LLM()
    return await llm.reason()

@dataclass
class Node:
    value: int
    left: Optional['Node']
    right: Optional['Node']

async def f_dataclass_2() -> Node:
    llm = LLM()
    return await llm.reason()

async def main():
    print(await f_dataclass_2())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())