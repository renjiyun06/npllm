import ast
from abc import ABC, abstractmethod
from typing import Type, Optional, Union
from types import FunctionType, MethodType

class RuntimeContext(ABC):
    @abstractmethod
    def get_class(self, class_name: str, enclosing_class: Optional[Type]=None) -> Optional[Type]:
        pass

    @abstractmethod
    def get_class_source(self, cls: Type) -> str:
        pass

    @abstractmethod
    def get_function_source(self, func: Union[FunctionType, MethodType]) -> str:
        pass