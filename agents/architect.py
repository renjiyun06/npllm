import asyncio
from typing import List
from dataclasses import dataclass

from prompt_toolkit import PromptSession

from npllm.core.llm import LLM
from npllm.core.code_context import ClassCodeContext

import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

@dataclass
class ChatMessage:
    name: str
    # always use the same language as the user
    content: str

    def __str__(self):
        return f"{self.name}: {self.content}"

class Architect(LLM):
    """
    Name: Broccoli

    Role Definition:
    Senior system architect with Linus-style: straightforward, pragmatic, pursuing simplicity

    Core Style:
    - Outspoken, pragmatic
    - Against over-engineering
    - Pursuing essence and performance

    Responsibilities:
    - Help analyze problems - dig into root causes, question assumptions, prioritize
    - Help design architecture - based on requirements, reasonable selection, weigh pros and cons, phased implementation
    
    Communication Style - concise and direct, criticism with evidence, sincere recognition
    """
    def __init__(self):
        LLM.__init__(self, code_context=ClassCodeContext())
        self._prompt_session = PromptSession()
        self._history: List[ChatMessage] = []

    async def run(self):
        while True:
            user_input = await self._prompt_session.prompt_async("User: ")
            if user_input in ('exit', 'quit'):
                print("Bye!")
                exit(0)

            self._history.append(ChatMessage(name="User", content=user_input))
            message: ChatMessage = await self.chat(self._history)
            print(f"{message.name}: {message.content}")
            self._history.append(message)

if __name__ == "__main__":
    architect = Architect()
    asyncio.run(architect.run())