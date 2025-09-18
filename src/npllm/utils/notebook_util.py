from typing import Optional, List, Dict
from types import FrameType
import inspect

def get_cells() -> Optional[List[str]]:
    """Get all the cells in a Jupyter notebook as a list of strings, or None if not available"""
    try:
        import __main__
        if hasattr(__main__, 'In'):
            cells = __main__.In
            return cells
        return None
    except:
        return None

def cell_source(i: int) -> Optional[str]:
    """Get the source code of the i-th cell in a Jupyter notebook, or None if not available"""
    cells = get_cells()
    if not cells:
        return None
    
    if i < 0:
        i = len(cells) + i
    
    if i < 0 or i >= len(cells):
        return None
    
    return cells[i]
    
def last_cell_source() -> Optional[str]:
    return cell_source(-1)

def is_in_notebook(frame: FrameType) -> bool:
    """Check if the given frame is in a Jupyter notebook environment"""
    try:
        import __main__
        if hasattr(__main__, 'In'):
            frame_info = inspect.getframeinfo(frame)
            if frame_info.filename and frame_info.filename.index("ipykernel") != -1:
                return True
        return False
    except:
        return False
    
def get_dataclass_source(cls) -> Optional[str]:
    """
    Get the source code of a dataclass defined in a Jupyter notebook cell.

    Here we use a simple matching strategy:
    1. Look for the cell that has the @dataclass decorator followed by the class definition.
    2. If found, use the indentation level of the class definition to capture the entire class body.
    """
    class_name = cls.__name__
    
    cells = get_cells()
    if not cells:
        return None
    
    for cell in cells:
        if not cell or not isinstance(cell, str):
            continue
        
        source_lines = cell.splitlines()
        start_line = None
        indent_level = None
        for i in range(len(source_lines)):
            line = source_lines[i]
            if line.strip().startswith("@dataclass"):
                # look for the next line that defines the class
                if i + 1 < len(source_lines):
                    next_line = source_lines[i + 1]
                    if next_line.strip().startswith(f"class {class_name}"):
                        # found the class definition position
                        start_line = i + 1
                        indent_level = len(next_line) - len(next_line.lstrip())
                        break
        if start_line is not None:
            # capture the class body based on indentation
            class_lines = []
            for j in range(start_line, len(source_lines)):
                line = source_lines[j]
                if j == start_line or (len(line) - len(line.lstrip()) >= indent_level):
                    class_lines.append(line)
                else:
                    break
            
            # remove the trailing empty lines
            while class_lines and not class_lines[-1].strip():
                class_lines.pop()
            return "\n".join(class_lines)
    return None

