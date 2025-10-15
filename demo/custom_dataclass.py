import npllm

from dataclasses import dataclass

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

user: User = reason('Create a user with name "John", age 25, and address "123 Main St, Anytown, USA, 12345"')
print(user)