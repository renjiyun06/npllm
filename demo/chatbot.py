import asyncio
from dataclasses import dataclass
from typing import List

from prompt_toolkit import PromptSession

from npllm.core.ai import AI
from npllm.core.execute_engines.default.default_execution_engine import DefaultExecutionEngine

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

class ChatBot(AI):
    def __init__(self):
        AI.__init__(self, semantic_execute_engine=DefaultExecutionEngine(compile_model="openrouter/google/gemini-2.5-pro"))
        self._prompt_session = PromptSession()
        self._history: List[ChatMessage] = []

    async def run(self):
        while True:
            user_input = await self._prompt_session.prompt_async("User: ")
            if user_input in ('exit', 'quit'):
                print("Bye!")
                exit(0)

            self._history.append(ChatMessage(name="User", content=user_input))
            # the chat bot's name is Tomato
            message: ChatMessage = await self.chat(self._history)
            print(f"{message.name}: {message.content}")
            self._history.append(message)

async def main():
    chatbot = ChatBot()
    await chatbot.run()

if __name__ == "__main__":
    asyncio.run(main())