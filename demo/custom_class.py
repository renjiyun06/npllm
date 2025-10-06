from dataclasses import dataclass

from npllm.core.llm import LLM

@dataclass
class Address:
    street: str
    city: str
    state: str
    zip: str

@dataclass
class User:
    name: str
    age: int
    address: Address

llm = LLM()
user: User = llm.reason('Create a user with name "John", age 25, and address "123 Main St, Anytown, USA, 12345"')
print(user)
