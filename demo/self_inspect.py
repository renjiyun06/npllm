import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

from dataclasses import dataclass
from typing import List
from prompt_toolkit import PromptSession

from npllm.core.llm import LLM

class Assistant(LLM):
    """
    You are a helpful assistant, your name is Tomato.
    """
    def __init__(self):
        LLM.__init__(self, model="openrouter/google/gemini-2.5-pro")

self_inspect = LLM.self_inspect(Assistant)

@dataclass
class Message:
    name: str
    # Always use the same language as the user
    content: str

class ChatBot:
    def __init__(self):
        self._prompt_session = PromptSession()
        self._session: List[Message] = []
        self.tomato = Assistant()

    @self_inspect
    def run(self):
        while True:
            self.wait_user_input()
            self.tomato_input()

    @self_inspect
    def wait_user_input(self):
        user_input = self._prompt_session.prompt("User: ")
        if (self._exit()):
            print("Bye!")
            exit(0)
        self._session.append(Message(name="User", content=user_input))
    
    @self_inspect
    def tomato_input(self):
        message: Message = self.tomato.reason(self._session)
        self._session.append(message)
        print(f"{message.name}: {message.content}")

    @self_inspect
    def _exit(self) -> bool:
        user_inputs = [msg.content for msg in self._session if msg.name == "User"]
        if len(user_inputs) >= 8 and user_inputs[-8:] == ["7", "4", "2", "8", "1", "3", "3", "1"]:
            return True

def main():
    bot = ChatBot()
    bot.run()

if __name__ == "__main__":
    main()