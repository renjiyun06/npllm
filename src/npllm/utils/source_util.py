from typing import List, Optional

def remove_indentation(source_code: str) -> Optional[str]:
    """Remove common leading indentation from all lines in the source code"""
    if not source_code:
        return None

    lines = source_code.splitlines()
    if not lines:
        return source_code

    ident = len(lines[0]) - len(lines[0].lstrip())
    if ident <= 0:
        return source_code
    trimmed_lines = [line[ident:] if len(line) >= ident else line for line in lines]
    return "\n".join(trimmed_lines)

def add_line_number(source_code_lines: List[str]) -> str:
    """Add line numbers to the source code lines"""
    if not source_code_lines:
        return ""
    
    max_line_num = len(source_code_lines)
    width = len(str(max_line_num))
    numbered_lines = [f"{i + 1:>{width}} | {line}" for i, line in enumerate(source_code_lines)]
    return "\n".join(numbered_lines)