import re
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class TemplateSyntax:
    var_start: str
    var_end: str
    loop_start: str
    loop_middle: str
    loop_start_end: str
    loop_end: str
    
    def __post_init__(self):
        for field in ['var_start', 'var_end', 'loop_start', 'loop_middle', 'loop_start_end', 'loop_end']:
            if not isinstance(getattr(self, field), str):
                raise RuntimeError(f"{field} must be a string")
        
        if self.var_start == self.var_end:
            raise RuntimeError("var_start and var_end must be different")


class MetaTemplate:
    def __init__(self, syntax: TemplateSyntax, remove_empty_lines: bool = True):
        self.syntax = syntax
        self.remove_empty_lines = remove_empty_lines
        self._compile_patterns()
    
    def _compile_patterns(self):
        var_start_escaped = re.escape(self.syntax.var_start)
        var_end_escaped = re.escape(self.syntax.var_end)
        loop_start_escaped = re.escape(self.syntax.loop_start)
        loop_middle_escaped = re.escape(self.syntax.loop_middle)
        loop_start_end_escaped = re.escape(self.syntax.loop_start_end)
        
        self.var_pattern = f"{var_start_escaped}([^{re.escape(self.syntax.var_end[0])}]+){var_end_escaped}"
        
        self.loop_start_pattern = (
            f"{loop_start_escaped}"
            f"([^\\s]+)"
            f"{loop_middle_escaped}"
            f"(\\w+)"
            f"{loop_start_end_escaped}"
        )
    
    def render(self, template: str, context: Dict[str, Any]) -> str:
        result = self._render_content(template, context)
        
        if self.remove_empty_lines:
            result = self._clean_empty_lines(result)
        
        return result
    
    def _clean_empty_lines(self, content: str) -> str:
        lines = content.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            is_empty = len(line.strip()) == 0
            
            if len(cleaned_lines) == 0:
                cleaned_lines.append(line)
                prev_empty = is_empty
            elif is_empty and prev_empty:
                continue
            else:
                cleaned_lines.append(line)
                prev_empty = is_empty
        
        while cleaned_lines and len(cleaned_lines[-1].strip()) == 0:
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def _render_content(self, content: str, context: Dict[str, Any]) -> str:
        content = self._process_loops(content, context)
        content = self._replace_variables(content, context)
        
        return content
    
    def _process_loops(self, content: str, context: Dict[str, Any]) -> str:
        while self.syntax.loop_start in content:
            loop_start_pos = content.find(self.syntax.loop_start)
            if loop_start_pos == -1:
                break
            
            line_start = content.rfind('\n', 0, loop_start_pos) + 1
            line_end = content.find('\n', loop_start_pos)
            if line_end == -1:
                line_end = len(content)
            
            loop_header_end = content.find(self.syntax.loop_start_end, loop_start_pos)
            if loop_header_end == -1:
                break
            
            loop_header_end += len(self.syntax.loop_start_end)
            loop_header = content[loop_start_pos:loop_header_end]
            
            loop_start_line = content[line_start:line_end]
            is_loop_start_alone = loop_start_line.strip() == loop_header.strip()
            
            match = re.match(self.loop_start_pattern, loop_header)
            if not match:
                break
            
            collection_path = match.group(1)
            item_name = match.group(2)
            
            pos = loop_header_end
            depth = 1
            loop_end_pos = -1
            
            while pos < len(content) and depth > 0:
                next_start = content.find(self.syntax.loop_start, pos)
                next_end = content.find(self.syntax.loop_end, pos)
                
                if next_end == -1:
                    break
                
                if next_start != -1 and next_start < next_end:
                    depth += 1
                    pos = next_start + len(self.syntax.loop_start)
                else:
                    depth -= 1
                    if depth == 0:
                        loop_end_pos = next_end
                    pos = next_end + len(self.syntax.loop_end)
            
            if loop_end_pos == -1:
                break
            
            end_line_start = content.rfind('\n', 0, loop_end_pos) + 1
            end_line_end = content.find('\n', loop_end_pos + len(self.syntax.loop_end))
            if end_line_end == -1:
                end_line_end = len(content)
            
            loop_end_line = content[end_line_start:end_line_end]
            is_loop_end_alone = loop_end_line.strip() == self.syntax.loop_end.strip()
            
            loop_body = content[loop_header_end:loop_end_pos]
            
            if is_loop_start_alone and loop_body.startswith('\n'):
                loop_body = loop_body[1:]
            
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
            
            if is_loop_start_alone and is_loop_end_alone:
                replace_start = line_start
                replace_end = end_line_end
                if replace_end < len(content) and content[replace_end-1:replace_end] != '\n':
                    if replace_end < len(content) and content[replace_end] == '\n':
                        replace_end += 1
            else:
                replace_start = loop_start_pos
                replace_end = loop_end_pos + len(self.syntax.loop_end)
            
            content = content[:replace_start] + replacement + content[replace_end:]
        
        return content
    
    def _replace_variables(self, content: str, context: Dict[str, Any]) -> str:
        def replace_var(match):
            path = match.group(1).strip()
            value = self._get_value(path, context)
            return str(value) if value is not None else ''
        
        return re.sub(self.var_pattern, replace_var, content)
    
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


class TemplateSyntaxPresets:
    @staticmethod
    def a_style():
        return TemplateSyntax(
            var_start="<<",
            var_end=">>",
            loop_start="<:loop ",
            loop_middle=" as ",
            loop_start_end=":>",
            loop_end="<:/loop:>"
        )

    @staticmethod
    def b_style():
        return TemplateSyntax(
            var_start="<%= ",
            var_end=" %>",
            loop_start="<% ",
            loop_middle=".each do |",
            loop_start_end="| %>",
            loop_end="<% end %>"
        )

def _build_context(args: List[Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    context = {}
    for i, arg in enumerate(args):
        context[f"arg{i}"] = arg

    for key, value in kwargs.items():
        context[key] = value

    return context

def tempate_a_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    template_a = MetaTemplate(TemplateSyntaxPresets.a_style())
    context = _build_context(args, kwargs)
    return template_a.render(template, context)

def tempate_b_placeholder_handler(template: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
    template_b = MetaTemplate(TemplateSyntaxPresets.b_style())
    context = _build_context(args, kwargs)
    return template_b.render(template, context)

if __name__ == "__main__":
    template = """
<% users.each do |user| %>
- <%= user.name %> (<%= user.age %>)
    <% user.tags.each do |tag| %>
    #<%= tag %>
    <% end %>
<% end %>
""".strip()

    context = {
        "name": "John",
        "users": [
            {
                "name": "John",
                "age": 30,
                "tags": ["tag1", "tag2"]
            }
        ]
    }
    print(tempate_b_placeholder_handler(template, [], context))