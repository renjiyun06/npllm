import json
from typing import Any

import json_repair

from npllm.core.annotated_type import AnnotatedType

def clean_json_str(json_str: str) -> str:
    if json_str.startswith("```json"):
        json_str = json_str[len("```json"):-len("```")].strip()
    elif json_str.startswith("```"):
        json_str = json_str[len("```"):-len("```")].strip()
    elif json_str.startswith("`"):
        json_str = json_str[len("`"):-len("`")].strip()
    return json_str

def parse_json_str(json_str: str, expected_type: AnnotatedType) -> Any:
    json_str = clean_json_str(json_str)
    json_value = None
    if (
        json_str.startswith("{") and json_str.endswith("}") or 
        json_str.startswith("[") and json_str.endswith("]") or
        json_str in ["true", "false", "null"] or
        json_str.isdigit()
    ):
        json_value = json_repair.loads(json_str)
    elif json_str.startswith('"') and json_str.endswith('"'):
        try:
            json_value = json.loads(json_str)
        except Exception as e:
            # it means the response content is a json string, but not correctly escaped
            # just let the whole string as the json value
            json_value = json_str
    else:
        json_value = json_str

    if str(expected_type) == "str" and isinstance(json_value, dict) and len(json_value.keys()) == 1:
        json_value = json_value[list(json_value.keys())[0]]

    return json_value