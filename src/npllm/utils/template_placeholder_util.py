import re
from typing import List, Any, Dict, Union

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

class TemplateA:
    def __init__(self, template: str):
        self.template = template
        self.lines = template.split('\n')
        
    def render(self, context: Dict[str, Any]) -> str:
        return self._render_lines(self.lines, context, 0)
    
    def _render_lines(self, lines: List[str], context: Dict[str, Any], base_indent: int) -> str:
        result = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            each_match = re.match(r'^(\s*)@each\s+(\w+)\s*<-\s*(.+?):\s*$', line)
            if each_match:
                indent = each_match.group(1)
                item_name = each_match.group(2)
                collection_path = each_match.group(3)
                
                body_lines, end_idx = self._extract_block(lines, i, len(indent))
                
                loop_result = self._render_each(collection_path, item_name, body_lines, context)
                result.extend(loop_result)
                
                i = end_idx + 1
            else:
                result.append(self._replace_variables(line, context))
                i += 1
        
        return '\n'.join(result)
    
    def _extract_block(self, lines: List[str], start_idx: int, indent_level: int) -> tuple[List[str], int]:
        block = []
        i = start_idx + 1
        
        first_line_indent = None
        temp_i = i
        while temp_i < len(lines) and first_line_indent is None:
            if lines[temp_i].strip():
                first_line_indent = len(lines[temp_i]) - len(lines[temp_i].lstrip())
                break
            temp_i += 1
        
        if first_line_indent is None:
            return [], start_idx
        
        while i < len(lines):
            line = lines[i]
            
            if not line.strip():
                block.append(line)
                i += 1
                continue
            
            current_indent = len(line) - len(line.lstrip())
            if current_indent < first_line_indent:
                break
            
            block.append(line)
            
            i += 1
        
        return block, i - 1
    
    def _render_each(self, collection_path: str, item_name: str, 
                     body_lines: List[str], context: Dict[str, Any]) -> List[str]:
        collection = self._get_value(collection_path, context)
        if not collection or not hasattr(collection, '__iter__'):
            return []
        
        result = []
        for item in collection:
            loop_context = context.copy()
            loop_context[item_name] = item
            
            body_result = []
            i = 0
            while i < len(body_lines):
                line = body_lines[i]
                
                each_match = re.match(r'^(\s*)@each\s+(\w+)\s*<-\s*(.+?):\s*$', line)
                if each_match:
                    nested_indent = each_match.group(1)
                    nested_item = each_match.group(2)
                    nested_collection = each_match.group(3)
                    
                    nested_body, end_idx = self._extract_block(body_lines, i, len(nested_indent))
                    
                    nested_result = self._render_each(nested_collection, nested_item, 
                                                    nested_body, loop_context)
                    body_result.extend(nested_result)
                    
                    i = end_idx + 1
                else:
                    body_result.append(self._replace_variables(line, loop_context))
                    i += 1
            
            result.extend(body_result)
        
        return result
    
    def _replace_variables(self, line: str, context: Dict[str, Any]) -> str:
        line = re.sub(
            r'@\{([^}]+)\}',
            lambda m: str(self._get_value(m.group(1), context)),
            line
        )
        
        line = re.sub(
            r'@([\w\.]+)(?![\w\.])',
            lambda m: str(self._get_value(m.group(1), context)),
            line
        )
        
        return line
    
    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        try:
            parts = path.split('.')
            value = context
            
            for i, part in enumerate(parts):
                if '[' in part and ']' in part:
                    name, idx_str = part.split('[')
                    idx = int(idx_str.rstrip(']'))
                    
                    if name:
                        if isinstance(value, dict):
                            value = value.get(name)
                        else:
                            value = getattr(value, name, None)
                    
                    if value is not None and hasattr(value, '__getitem__'):
                        value = value[idx]
                    else:
                        return ''
                else:
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif hasattr(value, part):
                        value = getattr(value, part)
                    else:
                        return ''
                
                if value is None:
                    return ''
            
            return value if value is not None else ''
        except:
            return ''

class TemplateB:
    def __init__(self, template: str):
        self.template = template
        
    def render(self, context: Dict[str, Any]) -> str:
        return self._render_content(self.template, context)
    
    def _render_content(self, content: str, context: Dict[str, Any]) -> str:
        content = self._process_loops(content, context)
        content = self._replace_variables(content, context)
        return content
    
    def _process_loops(self, content: str, context: Dict[str, Any]) -> str:
        while '<:loop' in content:
            loop_start = content.find('<:loop')
            if loop_start == -1:
                break
            
            loop_header_end = content.find(':>', loop_start)
            if loop_header_end == -1:
                break
                
            loop_header = content[loop_start:loop_header_end + 2]
            match = re.match(r'<:loop\s+([^\s]+)\s+as\s+(\w+):>', loop_header)
            if not match:
                break
                
            collection_path = match.group(1)
            item_name = match.group(2)
            
            pos = loop_header_end + 2
            depth = 1
            loop_end = -1
            
            while pos < len(content) and depth > 0:
                next_start = content.find('<:loop', pos)
                next_end = content.find('<:/loop:>', pos)
                
                if next_end == -1:
                    break
                    
                if next_start != -1 and next_start < next_end:
                    depth += 1
                    pos = next_start + 6
                else:
                    depth -= 1
                    if depth == 0:
                        loop_end = next_end
                    pos = next_end + 9
            
            if loop_end == -1:
                break
                
            loop_body = content[loop_header_end + 2:loop_end]
            
            collection = self._get_value(collection_path, context)
            if not collection or not hasattr(collection, '__iter__'):
                replacement = ''
            else:
                results = []
                for item in collection:
                    loop_context = context.copy()
                    loop_context[item_name] = item
                    rendered = self._render_content(loop_body, loop_context)
                    results.append(rendered)
                replacement = ''.join(results)
            
            content = content[:loop_start] + replacement + content[loop_end + 9:]
        
        return content
    
    def _replace_variables(self, content: str, context: Dict[str, Any]) -> str:
        variable_pattern = r'<<([^>]+)>>'
        
        def replace_var(match):
            path = match.group(1)
            value = self._get_value(path, context)
            return str(value) if value is not None else ''
        
        return re.sub(variable_pattern, replace_var, content)
    
    def _get_value(self, path: str, context: Dict[str, Any]) -> Any:
        try:
            path = path.strip()
            parts = path.split('.')
            value = context
            
            for part in parts:
                if '[' in part and ']' in part:
                    name, idx_str = part.split('[', 1)
                    idx = int(idx_str.rstrip(']'))
                    
                    if name:
                        if isinstance(value, dict):
                            value = value.get(name)
                        else:
                            value = getattr(value, name, None)
                    
                    if value and hasattr(value, '__getitem__'):
                        value = value[idx]
                    else:
                        return None
                else:
                    if isinstance(value, dict):
                        value = value.get(part)
                    elif hasattr(value, part):
                        value = getattr(value, part)
                    else:
                        return None
                
                if value is None:
                    return None
            
            return value
        except:
            return None
        
def template_a_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    context = {}
    for i, arg in enumerate(args):
        context[f"arg{i}"] = arg

    for key, value in kwargs.items():
        context[key] = value

    return TemplateA(template).render(context)

def template_b_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    context = {}
    for i, arg in enumerate(args):
        context[f"arg{i}"] = arg

    for key, value in kwargs.items():
        context[key] = value

    return TemplateB(template).render(context)

from dataclasses import dataclass

@dataclass
class Message:
    name: str
    content: str

if __name__ == "__main__":
    template = """
@each message <- arg0:
    @message.name: @message.content
===
    """.strip()
    args = [
        [
            Message(name="John", content="Hello"),
            Message(name="Jane", content="World"),
        ]
    ]
    kwargs = {}
    print(template_a_placeholder_handler(template, args, kwargs))