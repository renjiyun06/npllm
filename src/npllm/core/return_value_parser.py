from abc import ABC, abstractmethod

from npllm.utils.json_util import *

class ReturnValueParser(ABC):
    @abstractmethod
    def parse(self, expected_return_type, value):
        pass

class DefaultReturnValueParser(ReturnValueParser):
    def parse(self, expected_return_type, value):
        if is_json_null(value):
                return None
            
        if expected_return_type == 'str':
            if is_json_str(value):
                return value
            else:
                raise RuntimeError(f"{value} is not a valid JSON string")
        
        if expected_return_type == 'int':
            if is_json_number(value):
                return int(value)
            else:
                raise RuntimeError(f"{value} is not a valid JSON number")
            
        if expected_return_type == 'float':
            if is_json_number(value):
                return float(value)
            else:
                raise RuntimeError(f"{value} is not a valid JSON number")
            
        if expected_return_type == 'bool':
            if is_json_bool(value):
                return value
            else:
                raise RuntimeError(f"{value} is not a valid JSON boolean")
            
        if expected_return_type == 'List':
            if is_json_array(value):
                return [self.parse(expected_return_type.item_type, item) for item in value]
            else:
                raise RuntimeError(f"{value} is not a valid JSON array")
        
        if expected_return_type == 'Tuple':
            if is_json_array(value):
                if len(value) != len(expected_return_type.item_types):
                    raise RuntimeError(f"{value} does not match the expected tuple length {len(expected_return_type.item_types)}")
                return tuple(self.parse(item_type, item) for item_type, item in zip(expected_return_type.item_types, value))
            else:
                raise RuntimeError(f"{value} is not a valid JSON array")
            
        if expected_return_type == 'Dict':
            if is_json_object(value):
                return {self.parse(expected_return_type.key_type, k): self.parse(expected_return_type.value_type, v) for k, v in value.items()}
            else:
                raise RuntimeError(f"{value} is not a valid JSON object")

        if expected_return_type == 'Union':
            for type in expected_return_type.types:
                try:
                    result = self.parse(type, value)
                    if result is not None:
                        return result
                except RuntimeError as e:
                    continue
                
            raise RuntimeError(f"{value} does not match any type in the expected union types {expected_return_type.types}")
            
        if expected_return_type == 'Any':
            return value
        
        if expected_return_type == 'Optional':
            return self.parse(expected_return_type.item_type, value)
            
        if expected_return_type == "Literal":
            if value in expected_return_type.values:
                return value
            else:
                raise RuntimeError(f"{value} is not in the expected literal values {expected_return_type.values}")
            
        if expected_return_type == 'dataclass':
            if is_json_object(value):
                field_values = {}
                for field_name, field_type in expected_return_type.field_types.items():
                    if field_name in value:
                        field_values[field_name] = self.parse(field_type, value[field_name])
                    elif field_type == "Optional":
                        field_values[field_name] = None
                    else:
                        raise RuntimeError(f"Field {field_name} is missing in {value}")
                return expected_return_type.dataclass_cls(**field_values)
            else:
                raise RuntimeError(f"{value} is not a valid JSON object")
            
        if expected_return_type == 'alias':
            return self.parse(expected_return_type.original_type, value)
            
        raise RuntimeError(f"Unsupported expected_return_type: {expected_return_type}")