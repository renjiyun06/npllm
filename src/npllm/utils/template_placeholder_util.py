import re
from typing import List, Any, Dict

from jinja2 import Template, meta, Environment

import logging

logger = logging.getLogger(__name__)

def _placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any], placeholder_prefix: str, placeholder_suffix: str) -> str:
    placeholders = re.findall(rf"{placeholder_prefix}[a-zA-Z_][a-zA-Z0-9_.]+{placeholder_suffix}", template)
    print(placeholders)
    for original_placeholder in placeholders:   
        placeholder = original_placeholder
        placeholder = placeholder.replace(placeholder_prefix, "").replace(placeholder_suffix, "")
        
        root_obj = None
        dot_chain = []
        if placeholder.startswith("arg"):
            placeholder = placeholder[len("arg"):]
            position_index = int(placeholder.split(".")[0])
            root_obj = args[position_index]
            dot_chain = placeholder.split(".")[1:]
        else:
            root_obj = kwargs[placeholder.split(".")[0]]
            dot_chain = placeholder.split(".")[1:]

        value = root_obj
        for field in dot_chain:
            if field.startswith("[") and field.endswith("]"):
                logger.warning(f"Subscript syntax is used in {original_placeholder}")
                field = field[1:-1]
                value = value[int(field)]
            else:
                value = getattr(value, field)

        formatted_value: List[str] = []
        if isinstance(value, list):
            for item in value:
                formatted_value.append(str(item))
        else:
            formatted_value.append(str(value))

        template = template.replace(original_placeholder, "\n".join(formatted_value))

    return template.strip()

def double_curly_braces_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    return _placeholder_handler(template, args, kwargs, "{{", "}}")

def double_angle_brackets_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    return _placeholder_handler(template, args, kwargs, "<<", ">>")

def double_dollar_braces_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    return _placeholder_handler(template, args, kwargs, "$$", "$$")

def jinja2_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    variables = meta.find_undeclared_variables(Environment().parse(template))
    namespace = {}
    for variable in variables:
        if variable.startswith("arg"):
            position_index = int(variable[len("arg"):].split(".")[0])
            namespace[variable] = args[position_index]
        else:
            namespace[variable] = kwargs[variable.split(".")[0]]

    return Template(template).render(**namespace)