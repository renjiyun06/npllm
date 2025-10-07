from dataclasses import dataclass

from npllm.core.ai import AI

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

ai = AI()
user: User = ai.reason('Create a user with name "John", age 25, and address "123 Main St, Anytown, USA, 12345"')
print(user)
