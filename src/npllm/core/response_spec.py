from abc import ABC

class ResponseSpec(ABC):
    pass

class DefaultResponseSpec(ResponseSpec):
    """
    RESULT SPEC:
    - Must return valid JSON between <RESULT> and </RESULT> tags that strictly matches JSON VALUE SPEC
    - Use compressed single-line JSON format
    - Properly escape all JSON string values
    - Use unquoted numbers unless string type is explicitly required

    JSON VALUE SPEC:
    - expected_return_type is str: return a JSON string quoted with double quotes with proper escaping
    - expected_return_type is int: return a JSON number without quotes and no decimal point
    - expected_return_type is float: return a JSON number without quotes, may include a decimal point
    - expected_return_type is bool: return a JSON true or false without quotes
    - expected_return_type is List: return a JSON array whose elements strictly adhere to expected_return_type's element type
    - expected_return_type is Tuple: return a JSON array whose elements strictly adhere to expected_return_type's element types
    - expected_return_type is Dict: return a JSON object whose keys and values strictly adhere to expected_return_type's key and value types
    - expected_return_type is Union: return a JSON value that strictly adheres to one of the types in the Union
    - expected_return_type is Optional: return a JSON value that strictly adheres to the inner type or null
    - expected_return_type is Any: return any valid JSON value
    - expected_return_type is Literal: return a JSON value that exactly matches one of the Literal values
    - expected_return_type is dataclass: return a JSON object whose keys and values strictly adhere to the dataclass's field types
    - expected_return_type is a alias type: recursively apply these rules based on the alias's underlying type

    REASONING SPEC:
    - role_understanding: Your understanding of your role within this specific program execution context
    - program_intent_analysis: Analysis of the program's overall intent and your position in the execution flow
    - computational_logic: The computational logic and decision process for this specific method call
    - program_coherence_strategy: How your output maintains consistency with the overall program flow and ensures program coherence
    - type_adherence_validation: How you ensured the output strictly adheres to the expected return type
    """

class InspectModeResponseSpec(ResponseSpec):
    """
    RESULT SPEC:
    - Must return valid JSON between <RESULT> and </RESULT> tags that strictly matches JSON VALUE SPEC
    - Use compressed single-line JSON format
    - Properly escape all JSON string values
    - Use unquoted numbers unless string type is explicitly required

    JSON VALUE SPEC:
    - expected_return_type is str: return a JSON string quoted with double quotes with proper escaping
    - expected_return_type is int: return a JSON number without quotes and no decimal point
    - expected_return_type is float: return a JSON number without quotes, may include a decimal point
    - expected_return_type is bool: return a JSON true or false without quotes
    - expected_return_type is List: return a JSON array whose elements strictly adhere to expected_return_type's element type
    - expected_return_type is Tuple: return a JSON array whose elements strictly adhere to expected_return_type's element types
    - expected_return_type is Dict: return a JSON object whose keys and values strictly adhere to expected_return_type's key and value types
    - expected_return_type is Union: return a JSON value that strictly adheres to one of the types in the Union
    - expected_return_type is Optional: return a JSON value that strictly adheres to the inner type or null
    - expected_return_type is Any: return any valid JSON value
    - expected_return_type is Literal: return a JSON value that exactly matches one of the Literal values
    - expected_return_type is dataclass: return a JSON object whose keys and values strictly adhere to the dataclass's field types
    - expected_return_type is a alias type: recursively apply these rules based on the alias's underlying type

    REASONING SPEC:
    - role_and_responsibility: Your role and responsibility in this specific execution context
    - program_logic_understanding: Your understanding of the current program snippet's logic and functionality
    - system_workflow_integration: How the current program snippet fits within and contributes to the overall system workflow
    - computational_decision_process: The computational logic and decision process for this specific method call
    - consistency_maintenance: How your output maintains consistency with both the current program flow and the overall system coherence
    - system_dependencies_analysis: Consideration of potential interactions or dependencies with other system parts
    - return_type_adherence: How you ensured the output strictly adheres to the expected return type
    """