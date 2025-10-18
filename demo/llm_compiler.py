from dataclasses import dataclass
from typing import List, Union, Optional, Literal

import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

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
    left: Union[Number, Boolean, Variable, 'BinaryOp', 'UnaryOp']
    op: Literal['+', '-', '*', '/', '>', '<', '>=', '<=', '==', '!=', 'and', 'or']
    right: Union[Number, Boolean, Variable, 'BinaryOp', 'UnaryOp']

@dataclass
class UnaryOp:
    op: Literal['-', 'not']
    operand: Union[Number, Boolean, Variable, BinaryOp, 'UnaryOp']

@dataclass
class Assignment:
    variable: Variable
    value: Union[Number, Boolean, Variable, BinaryOp, UnaryOp]

@dataclass
class IfStatement:
    condition: Union[Number, Boolean, Variable, BinaryOp, UnaryOp]
    # Statements to execute if condition is true
    then_block: List[Union[Assignment, 'IfStatement', 'WhileStatement']]  
    # Statements to execute if condition is false. Can be empty
    else_block: Optional[List[Union[Assignment, 'IfStatement', 'WhileStatement']]] = None

@dataclass
class WhileStatement:
    condition: Union[Number, Boolean, Variable, BinaryOp, UnaryOp]
    # Statements to execute as long as condition is true.
    body: List[Union[Assignment, IfStatement, 'WhileStatement']]


@dataclass
class Program:
    # Top-level statements of the program
    statements: List[Union[Assignment, IfStatement, WhileStatement]]

from npllm.core.ai import AI
from npllm.core.execute_engines.default.default_execution_engine import DefaultExecutionEngine

class LLMCompiler(AI):
    def __init__(self):
        AI.__init__(self, semantic_execute_engine=DefaultExecutionEngine())

    async def compile(self, program: str) -> Program:
        return await self.reason_and_generate(program=program)
    
if __name__ == "__main__":
    import asyncio

    def execute(ast):
        print(f"Executing AST: {ast}")
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
                elif stmt.else_block:
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
i = 0
while i < 10:
    sum = sum + i
    i = i + 1
""".strip()
        ast = await compiler.compile(program)
        execute(ast)

    asyncio.run(main())