import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

from dataclasses import dataclass
from typing import List, Union

@dataclass
class Number:
    value: float

@dataclass
class Boolean:
    value: bool

@dataclass
class Variable:
    name: str

@dataclass
class BinaryOp:
    left: 'Expression'
    # Operator: '+', '-', '*', '/', '>', '<', '>=', '<=', '==', '!=', 'and', 'or'
    op: str
    right: 'Expression'

@dataclass
class UnaryOp:
    # Operator: '-', 'not'
    op: str 
    operand: 'Expression'

Expression = Union[Number, Boolean, Variable, BinaryOp, UnaryOp]

@dataclass
class Assignment:
    variable: Variable
    value: Expression

@dataclass
class IfStatement:
    condition: Expression
    # Statements to execute if condition is true
    then_block: List['Statement']  
    # Statements to execute if condition is false. Can be empty
    else_block: List['Statement'] 

@dataclass
class WhileStatement:
    condition: Expression
    # Statements to execute as long as condition is true.
    body: List['Statement']

Statement = Union[Assignment, IfStatement, WhileStatement]

@dataclass
class Program:
    # Top-level statements of the program
    statements: List[Statement]

from npllm.core.llm import LLM

class LLMCompiler(LLM):
    """
    You are a compiler that strictly translates an imperative programming language into AST
    """
    def __init__(self):
        LLM.__init__(self)

    async def compile(self, program: str) -> Program:
        return await self.reason(program)
    
if __name__ == "__main__":
    import asyncio

    def execute(ast):
        env = {}
        def eval_expr(expr):
            if isinstance(expr, Number):
                return expr.value
            elif isinstance(expr, Boolean):
                return expr.value
            elif isinstance(expr, Variable):
                return env.get(expr.name, 0)
            elif isinstance(expr, BinaryOp):
                left = eval_expr(expr.left)
                right = eval_expr(expr.right)
                if expr.op == '+':
                    return left + right
                elif expr.op == '-':
                    return left - right
                elif expr.op == '*':
                    return left * right
                elif expr.op == '/':
                    return left / right
                elif expr.op == '>':
                    return left > right
                elif expr.op == '<':
                    return left < right
                elif expr.op == '>=':
                    return left >= right
                elif expr.op == '<=':
                    return left <= right
                elif expr.op == '==':
                    return left == right
                elif expr.op == '!=':
                    return left != right
                elif expr.op == 'and':
                    return left and right
                elif expr.op == 'or':
                    return left or right
            elif isinstance(expr, UnaryOp):
                operand = eval_expr(expr.operand)
                if expr.op == '-':
                    return -operand
                elif expr.op == 'not':
                    return not operand

        def exec_stmt(stmt):
            if isinstance(stmt, Assignment):
                env[stmt.variable.name] = eval_expr(stmt.value)
            elif isinstance(stmt, IfStatement):
                if eval_expr(stmt.condition):
                    for s in stmt.then_block:
                        exec_stmt(s)
                else:
                    for s in stmt.else_block:
                        exec_stmt(s)
            elif isinstance(stmt, WhileStatement):
                while eval_expr(stmt.condition):
                    for s in stmt.body:
                        exec_stmt(s)

        for statement in ast.statements:
            exec_stmt(statement)

        print(env)

    async def main():
        compiler = LLMCompiler()
        program = """
        sum = 0
        i = 1
        while i <= 100:
            sum = sum + i * 2
            i = i + 1
        """
        ast = await compiler.compile(program)
        execute(ast)

    asyncio.run(main())