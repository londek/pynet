# CS AST components

import ast
from dataclasses import dataclass

class AST():
    pass

@dataclass
class FieldDef(AST):
    visibility: str
    type: ast.Name
    target: ast.Name
    value: ast.expr | None
    static: bool

