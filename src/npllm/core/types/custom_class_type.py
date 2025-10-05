import ast
import inspect
import typing
from typing import Optional, Dict, Set, List
from types import ModuleType

from npllm.core.type import Type
from npllm.core.runtime_context import RuntimeContext

import logging

logger = logging.getLogger(__name__)

class CustomClassType(Type):
    @classmethod
    def _enclosing_custom_class_type(
        cls, 
        enclosing_type: Type
    ) -> Optional['CustomClassType']:
        current = enclosing_type
        while current:
            if isinstance(current, CustomClassType):
                return current
            current = current._enclosing_type
        return None

    @classmethod
    def _self_referencing_custom_class_type(
        cls, 
        custom_class_cls: typing.Type, 
        enclosing_type: Type
    ) -> Optional['CustomClassType']:
        current = enclosing_type
        while current:
            if (
                isinstance(current, CustomClassType) and 
                current._custom_class_cls == custom_class_cls
            ):
                return current
            current = current._enclosing_type
        return None

    @classmethod
    def from_annotation(
        cls, 
        annotation: ast.Name | ast.Constant, 
        runtime_context: RuntimeContext, 
        enclosing_type: Type
    ) -> Optional['CustomClassType']:
        class_name = None
        if isinstance(annotation, ast.Name):
            class_name = annotation.id
        elif isinstance(annotation, ast.Constant):
            class_name = annotation.value
        
        enclosing_custom_class = None
        enclosing_custom_class_type = cls._enclosing_custom_class_type(enclosing_type)
        if enclosing_custom_class_type:
            enclosing_custom_class = enclosing_custom_class_type._custom_class_cls
        
        custom_class_cls = runtime_context.get_class(class_name, enclosing_custom_class)
        if not custom_class_cls:
            raise RuntimeError(f"Cannot find custom class {class_name}")
        
        logger.debug(f"CustomClassType.from_annotation: {ast.dump(annotation)}...")
        self_referencing_custom_class_type = cls._self_referencing_custom_class_type(custom_class_cls, enclosing_type)
        if self_referencing_custom_class_type:
            logger.debug(f"CustomClassType.from_annotation: {class_name} is self-referencing")
            return self_referencing_custom_class_type
        
        custom_class_source = runtime_context.get_class_source(custom_class_cls)
        if not custom_class_source:
            raise RuntimeError(f"Cannot get source of custom class {class_name}")

        custom_class_type = CustomClassType(enclosing_type, class_name, custom_class_cls)
        logger.debug(f"CustomClassType.from_annotation: early created CustomClassType for {class_name} for self referencing")

        field_types = {}
        for node in ast.walk(ast.parse(custom_class_source)):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        field_name = stmt.target.id
                        field_type = Type.from_annotation(stmt.annotation, runtime_context, custom_class_type)
                        if not field_type:
                            raise RuntimeError(f"Cannot parse field type for {field_name} in custom class {class_name}")
                        field_types[field_name] = field_type
                
                custom_class_type._field_types = field_types
                logger.debug(f"CustomClassType.from_annotation: {ast.dump(annotation)}")
                return custom_class_type

        raise RuntimeError(f"Failed to parse custom class {class_name}")

    def __init__(
        self, 
        enclosing_type: Type, 
        custom_class_name: str, 
        custom_class_cls: typing.Type, 
        field_types: Optional[Dict[str, Type]]=None
    ):
        Type.__init__(self, enclosing_type)
        self._custom_class_name = custom_class_name
        self._custom_class_cls = custom_class_cls
        self._field_types = field_types or {}

    def runtime_type(self) -> typing.Type:
        return self._custom_class_cls

    def get_referenced_custom_classes(self, visited: Optional[Set['Type']]=None) -> List[typing.Type]:
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        result = []
        result.append(self._custom_class_cls)
        for field_type in self._field_types.values():
            result.extend(field_type.get_referenced_custom_classes(visited))
        return result

    def get_dependent_modules(self, visited: Optional[Set['Type']]=None) -> Set[ModuleType]:
        if visited is None:
            visited = set()
        if self in visited:
            return set()
        visited.add(self)
        dependent_modules = set()
        dependent_modules.add(inspect.getmodule(self._custom_class_cls))
        for field_type in self._field_types.values():
            dependent_modules.update(field_type.get_dependent_modules(visited))
        return dependent_modules

    def __str__(self):
        return f"{self._custom_class_name}"