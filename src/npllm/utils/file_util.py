from typing import List

def add_line_number(content: List[str]) -> str:
    """Add line numbers to the source code lines"""
    if not content:
        return ""
    
    max_line_num = len(content)
    width = len(str(max_line_num))
    numbered_lines = [f"{i + 1:>{width}} | {line}" for i, line in enumerate(content)]
    return "\n".join(numbered_lines)