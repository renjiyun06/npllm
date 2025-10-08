import hashlib
from typing import Union
from types import ModuleType

from npllm.core.notebook import Cell

def module_hash(module: Union[ModuleType, Cell]) -> str:
    if isinstance(module, ModuleType):
        with open(module.__file__, "r", encoding="utf-8") as f:
            return hashlib.md5(f.read().encode("utf-8")).hexdigest()
    else:
        return module.code_hash

def module_path(module: Union[ModuleType, Cell]) -> str:
    if isinstance(module, ModuleType):
        return module.__file__
    else:
        return module.fake_module_filename()