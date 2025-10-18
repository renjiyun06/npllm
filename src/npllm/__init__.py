import builtins
import sys
import os
import ast
import builtins
import inspect
from typing import Set
from importlib.abc import MetaPathFinder, SourceLoader
from importlib.util import spec_from_file_location
from importlib.machinery import ModuleSpec

from IPython import get_ipython

from npllm.core.ai import AI
from npllm.core.execute_engines.agent.agent_execution_engine import AgentExecutionEngine

import logging

logger = logging.getLogger(__name__)

_ai = AI(semantic_execute_engine=AgentExecutionEngine())
_enabled = False

_excluded: Set[str] = {
    '__annotations__', '__builtins__', '__doc__', '__loader__',
    '__name__', '__package__', '__spec__',
    'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
    'type', 'object', 'Exception', 'print', 'len', 'range'
}

def _enable_module_ai():
    global _ai, _excluded

    caller_frame = inspect.currentframe()
    while caller_frame and (__file__ in caller_frame.f_code.co_filename or "importlib._bootstrap" in caller_frame.f_code.co_filename):
        caller_frame = caller_frame.f_back
        
    if not caller_frame:
        return

    mod_globals = caller_frame.f_globals
    filename = caller_frame.f_code.co_filename

    with open(filename, 'r', encoding='utf-8') as f:
        src = f.read()

    tree = ast.parse(src)

    defined: Set[str] = set(mod_globals.keys())

    def add_target_names(node):
        if isinstance(node, ast.Name):
            defined.add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for elt in node.elts:
                add_target_names(elt)

    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(n.name)
        elif isinstance(n, ast.Import):
            for alias in n.names:
                defined.add(alias.asname or alias.name.split('.')[0])
        elif isinstance(n, ast.ImportFrom):
            for alias in n.names:
                defined.add(alias.asname or alias.name)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            defined.add(n.target.id)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                add_target_names(t)
        elif isinstance(n, ast.With):
            for item in n.items:
                if item.optional_vars:
                    add_target_names(item.optional_vars)

    to_inject: Set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            name = n.func.id
            if name.startswith('_'):
                continue
            if name in defined or name in _excluded:
                continue
            if hasattr(builtins, name):
                continue
            to_inject.add(name)

    logger.info(f"Injecting {to_inject} into {mod_globals}")

    for name in to_inject:
        mod_globals.setdefault(name, getattr(_ai, name))

class AIBase(AI):
    def __init__(self):
        AI.__init__(self, semantic_execute_engine=AgentExecutionEngine())

class ClassBaseInjector(ast.NodeTransformer):
    def __init__(self):
        self.has_classes = False
    
    def visit_ClassDef(self, node):
        self.has_classes = True
        
        if not node.bases:
            node.bases.append(ast.Name(id='_AIBase', ctx=ast.Load()))
        
        self.generic_visit(node)
        return node

class AISourceLoader(SourceLoader):
    def __init__(self, fullname, path):
        self.fullname = fullname
        self.path = path
    
    def get_filename(self, fullname):
        return self.path
    
    def get_data(self, path):
        with open(path, 'rb') as f:
            return f.read()
    
    def source_to_code(self, data, path, *, _optimize=-1):
        try:
            source = data.decode('utf-8')
            tree = ast.parse(source, path)
            
            transformer = ClassBaseInjector()
            tree = transformer.visit(tree)
            
            if transformer.has_classes:
                import_node = ast.ImportFrom(
                    module='npllm',
                    names=[ast.alias(name='AIBase', asname='_AIBase')],
                    level=0
                )
                tree.body.insert(0, import_node)
            
            ast.fix_missing_locations(tree)
            
            return compile(tree, path, 'exec', dont_inherit=True, optimize=_optimize)
        except SyntaxError:
            return compile(data, path, 'exec', dont_inherit=True, optimize=_optimize)

class AIMetaPathFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith('npllm'):
            return None
        
        if self._is_stdlib_module(fullname):
            return None
        
        if path is None:
            path = sys.path
        
        for search_path in path:
            if 'site-packages' in search_path or 'dist-packages' in search_path:
                continue
            
            module_path = os.path.join(search_path, fullname.replace('.', os.sep) + '.py')
            if os.path.isfile(module_path):
                loader = AISourceLoader(fullname, module_path)
                return spec_from_file_location(
                    fullname, 
                    module_path, 
                    loader=loader,
                    submodule_search_locations=None
                )
        return None
    
    def _is_stdlib_module(self, fullname):
        stdlib_modules = {
            'abc', 'ast', 'asyncio', 'builtins', 'collections', 'copy',
            'datetime', 'email', 'encodings', 'functools', 'importlib',
            'inspect', 'io', 'itertools', 'json', 'logging', 'os',
            'pathlib', 're', 'sys', 'time', 'types', 'typing', 'warnings',
            'weakref', 'xml', 'unittest', 'http', 'urllib', 'socket',
            'threading', 'multiprocessing', 'queue', 'contextlib'
        }
        
        top_level = fullname.split('.')[0]
        return top_level in stdlib_modules

def _enable_ai_base_inject():
    finder = AIMetaPathFinder()
    sys.meta_path.insert(0, finder)

def _enable_python_ai():
    global _enabled
    _enable_module_ai()
    _enable_ai_base_inject()
    _enabled = True

def _enable_ipython_ai(ipython):
    global _ai, _enabled, _excluded

    class InterceptingNamespace(dict):
        def __missing__(self, key):
            if key.startswith('_'):
                raise KeyError(key)

            if key in _excluded:
                raise KeyError(key)

            if hasattr(builtins, key):
                value = getattr(builtins, key)
                self[key] = value
                return value

            async def placeholder(*args, **kwargs):
                return await getattr(_ai, key)(*args, **kwargs)
            
            placeholder.__name__ = key
            self[key] = placeholder
            return placeholder

    _original_ns = ipython.user_ns
    ipython.user_ns = InterceptingNamespace(ipython.user_ns)
    
    _enabled = True

def enable_ai():
    if _enabled:
        return
    
    ipython = get_ipython()
    if ipython:
        _enable_ipython_ai(ipython)
    else:
        _enable_python_ai()

enable_ai()
