import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

from dataclasses import dataclass
from typing import List, Union, Optional

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
    else_block: Optional[List['Statement']] = None

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
        LLM.__init__(self, model="openrouter/google/gemini-2.5-flash")

    async def compile(self, program: str) -> Program:
        return await self.reason(program)
    
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
                    # print(f"While loop condition {stmt.condition} is true in env {env}, executing body")
                    for s in stmt.body:
                        exec_stmt(s)

        for statement in ast.statements:
            exec_stmt(statement)

        print(env)

    async def main():
        compiler = LLMCompiler()
        program = """
score = 85
bonus = 0
grade = 0
scholarship = 0
total_students = 100
current_student = 1
excellent_count = 0
total_score = 0

while current_student <= total_students:
    if current_student % 10 == 0:
        score = score + 15
    else:
        if current_student % 5 == 0:
            score = score + 10
        else:
            score = score - 5
    
    if score > 100:
        score = 100
    else:
        if score < 0:
            score = 0
    
    bonus = 0
    if score >= 90 and current_student % 3 == 0:
        bonus = 5
    
    final_score = score + bonus
    if final_score > 100:
        final_score = 100
    
    if final_score >= 90:
        grade = 4
        scholarship = scholarship + 1000
        excellent_count = excellent_count + 1
    else:
        if final_score >= 80:
            grade = 3
            scholarship = scholarship + 500
        else:
            if final_score >= 70:
                grade = 2
                scholarship = scholarship + 200
            else:
                if final_score >= 60:
                    grade = 1
                else:
                    grade = 0
    
    total_score = total_score + final_score
    
    current_student = current_student + 1

average_score = total_score / total_students
excellent_rate = excellent_count * 100 / total_students

if excellent_rate >= 20 and average_score >= 75:
    scholarship = scholarship + excellent_count * 200
else:
    if excellent_rate >= 10 or average_score >= 70:
        scholarship = scholarship + excellent_count * 100

if scholarship > 50000:
    scholarship = 50000
"""
        ast = await compiler.compile(program)
        execute(ast)

    asyncio.run(main())