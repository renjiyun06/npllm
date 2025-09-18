import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.WARNING)

from prompt_toolkit.shortcuts import PromptSession
from dataclasses import dataclass
from typing import List

from npllm.core.llm import LLM

@dataclass
class Message:
    name: str
    # Always use the same language as the user
    content: str

class SimpleChatBot(LLM):
    def __init__(self):
        LLM.__init__(self)
        self.name = "SimpleChatBot"
        self.prompt_session = PromptSession()
        self.session: List[Message] = []

    async def run(self):
        while True:
            user_input = await self.prompt_session.prompt_async("User: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Bye!")
                break
            self.session.append(Message(name="User", content=user_input))
            response: Message = await self.chat(self.session, self.name)
            self.session.append(response)
            print(f"{response.name}: {response.content}")

if __name__ == "__main__":
    import asyncio
    bot = SimpleChatBot()
    asyncio.run(bot.run())