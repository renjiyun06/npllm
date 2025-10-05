import inspect
import sys
from types import FrameType, FunctionType, MethodType, ModuleType
from typing import Optional, Type

def is_module_frame(frame: FrameType) -> bool:
    return frame.f_code.co_name == "<module>"

def get_global_function_object(frame: FrameType) -> Optional[FunctionType]:
    if is_module_frame(frame):
        return None

    if 'self' in frame.f_locals or 'cls' in frame.f_locals:
        return None

    code_name = frame.f_code.co_name
    if code_name in frame.f_globals:
        obj = frame.f_globals[code_name]
        
        if isinstance(obj, FunctionType):
            if '.' not in obj.__qualname__:
                return obj
    
    return None

def get_instance_method_object(frame: FrameType) -> Optional[MethodType]:
    if is_module_frame(frame):
        return None

    if 'self' not in frame.f_locals:
        return None

    self_obj = frame.f_locals['self']

    try:
        code_name = frame.f_code.co_name
        method = getattr(self_obj, code_name)
        
        if isinstance(method, MethodType):
            if method.__func__.__code__ == frame.f_code:
                return method
    except AttributeError:
        pass
    
    return None

def get_module_object(frame: FrameType) -> Optional[ModuleType]:
    module_name = frame.f_globals.get('__name__')
    if module_name and module_name in sys.modules:
        return sys.modules[module_name]
    
    return None

def get_method_defining_class(method: MethodType) -> Optional[Type]:
    func = method.__func__
    for klass in inspect.getmro(func.__self__.__class__):
        if method.__name__ in klass.__dict__:
            if klass.__dict__[method.__name__] is func:
                return klass
        
    return None

def get_class_from_module(class_name: str, module: ModuleType) -> Optional[Type]:
    if class_name not in module.__dict__:
        return None

    obj = module.__dict__[class_name]

    if not inspect.isclass(obj):
        return None

    if obj.__module__ != module.__name__:
        return None

    return obj