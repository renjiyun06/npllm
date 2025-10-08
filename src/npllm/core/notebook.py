import hashlib
import json
from dataclasses import dataclass
from typing import List

from IPython import get_ipython
import ipynbname

@dataclass
class Cell:
    path: str
    id: str
    code: str
    code_hash: str

    def fake_module_filename(self) -> str:
        return f"{self.path}#{self.id}"

class Notebook:
    @classmethod
    def current_exec_cell(cls) -> Cell:
        path = ipynbname.path()
        notebook = Notebook(path)
        return notebook.find_cell_by_code(get_ipython().history_manager.input_hist_raw[-1])

    def __init__(self, path: str):
        self.path = path

    @property
    def cells(self) -> List[Cell]:
        with open(self.path, "r", encoding="utf-8") as f:
            notebook_data = json.load(f)
            cells = []
            for cell in notebook_data["cells"]:
                if cell["cell_type"] == "code":
                    id = cell["id"]
                    code = "".join(cell["source"]).rstrip("\n")
                    code_hash = hashlib.md5(code.encode(encoding="utf-8")).hexdigest()
                    cells.append(Cell(self.path, id, code, code_hash))
            return cells

    def find_cell_by_code(self, code: str) -> Cell:
        result = []
        for cell in self.cells:
            if cell.code == code:
                result.append(cell)
        
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            raise RuntimeError(f"Found multiple cells with the same code: {code}")
            
    def __hash__(self) -> int:
        return hash(self.path)

    def __eq__(self, other: 'Notebook') -> bool:
        if not isinstance(other, Notebook):
            return False

        return self.path == other.path
    
    def __str__(self) -> str:
        return f"Notebook(path={self.path})"