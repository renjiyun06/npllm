from abc import ABC

from npllm.utils.json_util import *

class ResponseSpec(ABC):
    pass

class DefaultResponseSpec(ResponseSpec):
    """
    RESULT SPEC:
    - Must return valid JSON between <RESULT> and </RESULT> tags that matches expected_return_type and can be successfully processed by return_type_mapping
    - Use compressed single-line JSON format
    - Properly escape all JSON string values
    - Use unquoted numbers unless string type is explicitly required

    REASONING SPEC:
    - role_understanding: Your understanding of your role within this specific program execution context
    - program_intent_analysis: Analysis of the program's overall intent and your position in the execution flow
    - computational_logic: The computational logic and decision process for this specific method call
    - program_coherence_strategy: How your output maintains consistency with the overall program flow and ensures program coherence
    - type_adherence_validation: How you ensured the output strictly adheres to the expected return type
    """

    @staticmethod
    def return_type_mapping(expected_return_type, value):
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
                return [DefaultResponseSpec.return_type_mapping(expected_return_type.item_type, item) for item in value]
            else:
                raise RuntimeError(f"{value} is not a valid JSON array")
        
        if expected_return_type == 'Tuple':
            if is_json_array(value):
                if len(value) != len(expected_return_type.item_types):
                    raise RuntimeError(f"{value} does not match the expected tuple length {len(expected_return_type.item_types)}")
                return tuple(DefaultResponseSpec.return_type_mapping(item_type, item) for item_type, item in zip(expected_return_type.item_types, value))
            else:
                raise RuntimeError(f"{value} is not a valid JSON array")
            
        if expected_return_type == 'Dict':
            if is_json_object(value):
                return {DefaultResponseSpec.return_type_mapping(expected_return_type.key_type, k): DefaultResponseSpec.return_type_mapping(expected_return_type.value_type, v) for k, v in value.items()}
            else:
                raise RuntimeError(f"{value} is not a valid JSON object")

        if expected_return_type == 'Union':
            for type in expected_return_type.types:
                try:
                    result = DefaultResponseSpec.return_type_mapping(type, value)
                    if result is not None:
                        return result
                except RuntimeError as e:
                    continue
                
            raise RuntimeError(f"{value} does not match any type in the expected union types {expected_return_type.types}")
            
        if expected_return_type == 'Any':
            return value
        
        if expected_return_type == 'Optional':
            return DefaultResponseSpec.return_type_mapping(expected_return_type.item_type, value)
            
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
                        field_values[field_name] = DefaultResponseSpec.return_type_mapping(field_type, value[field_name])
                    elif field_type == "Optional":
                        field_values[field_name] = None
                    else:
                        raise RuntimeError(f"Field {field_name} is missing in {value}")
                return expected_return_type.dataclass_cls(**field_values)
            else:
                raise RuntimeError(f"{value} is not a valid JSON object")
            
        if expected_return_type == 'alias':
            return DefaultResponseSpec.return_type_mapping(expected_return_type.original_type, value)
            
        raise RuntimeError(f"Unsupported expected_return_type: {expected_return_type}")

class InspectModeResponseSpec(ResponseSpec):
    """
    RESULT SPEC:
    - Must return valid JSON between <RESULT> and </RESULT> tags that matches expected_return_type and can be successfully processed by return_type_mapping
    - Use compressed single-line JSON format
    - Properly escape all JSON string values
    - Use unquoted numbers unless string type is explicitly required

    REASONING SPEC:
    - role_and_responsibility: Your role and responsibility in this specific execution context
    - program_logic_understanding: Your understanding of the current program snippet's logic and functionality
    - system_workflow_integration: How the current program snippet fits within and contributes to the overall system workflow
    - computational_decision_process: The computational logic and decision process for this specific method call
    - consistency_maintenance: How your output maintains consistency with both the current program flow and the overall system coherence
    - system_dependencies_analysis: Consideration of potential interactions or dependencies with other system parts
    - return_type_adherence: How you ensured the output strictly adheres to the expected return type
    """

    @staticmethod
    def return_type_mapping(expected_return_type, value):
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
                return [DefaultResponseSpec.return_type_mapping(expected_return_type.item_type, item) for item in value]
            else:
                raise RuntimeError(f"{value} is not a valid JSON array")
        
        if expected_return_type == 'Tuple':
            if is_json_array(value):
                if len(value) != len(expected_return_type.item_types):
                    raise RuntimeError(f"{value} does not match the expected tuple length {len(expected_return_type.item_types)}")
                return tuple(DefaultResponseSpec.return_type_mapping(item_type, item) for item_type, item in zip(expected_return_type.item_types, value))
            else:
                raise RuntimeError(f"{value} is not a valid JSON array")
            
        if expected_return_type == 'Dict':
            if is_json_object(value):
                return {DefaultResponseSpec.return_type_mapping(expected_return_type.key_type, k): DefaultResponseSpec.return_type_mapping(expected_return_type.value_type, v) for k, v in value.items()}
            else:
                raise RuntimeError(f"{value} is not a valid JSON object")

        if expected_return_type == 'Union':
            for type in expected_return_type.types:
                try:
                    result = DefaultResponseSpec.return_type_mapping(type, value)
                    if result is not None:
                        return result
                except RuntimeError as e:
                    continue
                
            raise RuntimeError(f"{value} does not match any type in the expected union types {expected_return_type.types}")
            
        if expected_return_type == 'Any':
            return value
        
        if expected_return_type == 'Optional':
            return DefaultResponseSpec.return_type_mapping(expected_return_type.item_type, value)
            
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
                        field_values[field_name] = DefaultResponseSpec.return_type_mapping(field_type, value[field_name])
                    elif field_type == "Optional":
                        field_values[field_name] = None
                    else:
                        raise RuntimeError(f"Field {field_name} is missing in {value}")
                return expected_return_type.dataclass_cls(**field_values)
            else:
                raise RuntimeError(f"{value} is not a valid JSON object")
            
        if expected_return_type == 'alias':
            return DefaultResponseSpec.return_type_mapping(expected_return_type.original_type, value)
            
        raise RuntimeError(f"Unsupported expected_return_type: {expected_return_type}")