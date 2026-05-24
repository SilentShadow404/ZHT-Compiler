from __future__ import annotations

from dataclasses import dataclass, field

from .ast import (
    Assignment,
    BinaryOp,
    Block,
    Call,
    ExpressionStatement,
    ForStatement,
    FunctionDef,
    Identifier,
    IfStatement,
    InputStatement,
    Literal,
    OutputStatement,
    Program,
    ReturnStatement,
    UnaryOp,
    VarDecl,
    WhileStatement,
)


@dataclass(slots=True)
class Instruction:
    op: str
    arg1: str | None = None
    arg2: str | None = None
    result: str | None = None

    def __str__(self) -> str:
        parts = [self.op]
        if self.arg1 is not None:
            parts.append(str(self.arg1))
        if self.arg2 is not None:
            parts.append(str(self.arg2))
        if self.result is not None:
            parts.append(str(self.result))
        return " | ".join(parts)


@dataclass
class IRProgram:
    instructions: list[Instruction] = field(default_factory=list)

    def emit(self, op: str, arg1: str | None = None, arg2: str | None = None, result: str | None = None) -> None:
        self.instructions.append(Instruction(op, arg1, arg2, result))

    def render(self) -> str:
        return "\n".join(str(instruction) for instruction in self.instructions)


class IRGenerator:
    def __init__(self) -> None:
        self.program = IRProgram()
        self.temp_index = 0
        self.label_index = 0

    def generate(self, program: Program) -> IRProgram:
        for declaration in program.declarations:
            self._visit_top_level(declaration)
        return self.program

    def _visit_top_level(self, node: object) -> None:
        if isinstance(node, FunctionDef):
            self._visit_function(node)
        elif isinstance(node, VarDecl):
            self._visit_var_decl(node)

    def _visit_function(self, function: FunctionDef) -> None:
        return_type = function.return_type.name if function.return_type else "empty"
        params = ", ".join(parameter.name for parameter in function.params)
        self.program.emit("function", function.name, return_type, params)
        if function.body is not None:
            self._visit_block(function.body)
        self.program.emit("end_function", function.name)

    def _visit_block(self, block: Block) -> None:
        for statement in block.statements:
            self._visit_statement(statement)

    def _visit_statement(self, statement: object) -> None:
        if isinstance(statement, Block):
            self._visit_block(statement)
        elif isinstance(statement, VarDecl):
            self._visit_var_decl(statement)
        elif isinstance(statement, Assignment):
            self._visit_assignment(statement)
        elif isinstance(statement, ExpressionStatement):
            self._gen_expr(statement.expression)
        elif isinstance(statement, IfStatement):
            self._visit_if(statement)
        elif isinstance(statement, WhileStatement):
            self._visit_while(statement)
        elif isinstance(statement, ForStatement):
            self._visit_for(statement)
        elif isinstance(statement, ReturnStatement):
            self._visit_return(statement)
        elif isinstance(statement, InputStatement):
            self.program.emit("read", statement.target.name if statement.target else None)
        elif isinstance(statement, OutputStatement):
            value = self._gen_expr(statement.value)
            self.program.emit("print", value)

    def _visit_var_decl(self, declaration: VarDecl) -> None:
        if declaration.initializer is None:
            self.program.emit("decl", declaration.type_node.name if declaration.type_node else None, declaration.name)
            return
        value = self._gen_expr(declaration.initializer)
        self.program.emit("assign", value, None, declaration.name)

    def _visit_assignment(self, statement: Assignment) -> None:
        value = self._gen_expr(statement.value)
        self.program.emit("assign", value, None, statement.target.name if statement.target else None)

    def _visit_if(self, statement: IfStatement) -> None:
        else_label = self._new_label("else")
        end_label = self._new_label("endif")
        condition = self._gen_expr(statement.condition)
        self.program.emit("ifz", condition, None, else_label)
        self._visit_statement(statement.then_branch)
        self.program.emit("goto", end_label)
        self.program.emit("label", else_label)
        if statement.else_branch is not None:
            self._visit_statement(statement.else_branch)
        self.program.emit("label", end_label)

    def _visit_while(self, statement: WhileStatement) -> None:
        start_label = self._new_label("while_start")
        end_label = self._new_label("while_end")
        self.program.emit("label", start_label)
        condition = self._gen_expr(statement.condition)
        self.program.emit("ifz", condition, None, end_label)
        self._visit_statement(statement.body)
        self.program.emit("goto", start_label)
        self.program.emit("label", end_label)

    def _visit_for(self, statement: ForStatement) -> None:
        start_label = self._new_label("for_start")
        end_label = self._new_label("for_end")
        if statement.init is not None:
            self._visit_statement(statement.init)
        self.program.emit("label", start_label)
        if statement.condition is not None:
            condition = self._gen_expr(statement.condition)
            self.program.emit("ifz", condition, None, end_label)
        self._visit_statement(statement.body)
        if statement.update is not None:
            self._gen_expr(statement.update)
        self.program.emit("goto", start_label)
        self.program.emit("label", end_label)

    def _visit_return(self, statement: ReturnStatement) -> None:
        if statement.value is None:
            self.program.emit("return")
            return
        value = self._gen_expr(statement.value)
        self.program.emit("return", value)

    def _gen_expr(self, expression: object) -> str:
        if expression is None:
            return ""
        if isinstance(expression, Literal):
            if isinstance(expression.value, bool):
                return "yes" if expression.value else "no"
            return str(expression.value)
        if isinstance(expression, Identifier):
            return expression.name
        if isinstance(expression, UnaryOp):
            operand = self._gen_expr(expression.operand)
            temp = self._new_temp()
            self.program.emit("unary", expression.operator, operand, temp)
            return temp
        if isinstance(expression, BinaryOp):
            left = self._gen_expr(expression.left)
            right = self._gen_expr(expression.right)
            temp = self._new_temp()
            self.program.emit("binary", expression.operator, f"{left}, {right}", temp)
            return temp
        if isinstance(expression, Call):
            for argument in expression.args:
                self.program.emit("param", self._gen_expr(argument))
            temp = self._new_temp()
            self.program.emit("call", expression.callee, str(len(expression.args)), temp)
            return temp
        if isinstance(expression, Assignment):
            value = self._gen_expr(expression.value)
            target = expression.target.name if expression.target else ""
            self.program.emit("assign", value, None, target)
            return target
        if isinstance(expression, ExpressionStatement):
            return self._gen_expr(expression.expression)
        return ""

    def _new_temp(self) -> str:
        self.temp_index += 1
        return f"t{self.temp_index}"

    def _new_label(self, prefix: str) -> str:
        self.label_index += 1
        return f"{prefix}_{self.label_index}"
