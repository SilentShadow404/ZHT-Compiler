from __future__ import annotations

from dataclasses import dataclass

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
from .symbols import Symbol, SymbolTable
from .zht_spec import TYPE_EMPTY, TYPE_FLAG, TYPE_REAL, TYPE_WHOLE


NUMERIC_TYPES = {TYPE_WHOLE, TYPE_REAL}
SCALAR_TYPES = {TYPE_WHOLE, TYPE_REAL, TYPE_FLAG}


@dataclass(slots=True)
class SemanticResult:
    errors: list[str]
    symbols: SymbolTable


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.symbols = SymbolTable()
        self.errors: list[str] = []
        self.current_function: Symbol | None = None

    def analyze(self, program: Program) -> SemanticResult:
        self._declare_top_level(program)
        for declaration in program.declarations:
            if isinstance(declaration, VarDecl):
                self._analyze_var_decl(declaration)
            elif isinstance(declaration, FunctionDef):
                self._analyze_function(declaration)
        return SemanticResult(self.errors, self.symbols)

    def _declare_top_level(self, program: Program) -> None:
        for declaration in program.declarations:
            if isinstance(declaration, VarDecl):
                self._declare_variable(declaration, global_scope=True)
            elif isinstance(declaration, FunctionDef):
                self._declare_function(declaration)

    def _declare_variable(self, declaration: VarDecl, global_scope: bool = False) -> None:
        type_name = declaration.type_node.name if declaration.type_node else "error"
        if type_name == TYPE_EMPTY:
            self.errors.append(f"Variable {declaration.name} cannot have type void at {declaration.line}:{declaration.column}")
            return
        if declaration.initializer is not None:
            initializer_type = self._expr_type(declaration.initializer)
            if not self._compatible(type_name, initializer_type):
                self.errors.append(
                    f"Type mismatch in declaration of {declaration.name} at {declaration.line}:{declaration.column}: "
                    f"expected {type_name}, got {initializer_type}"
                )
        symbol = Symbol(declaration.name, "var", type_name, self.symbols.level, line=declaration.line, column=declaration.column)
        if not self.symbols.define(symbol):
            self.errors.append(f"Redeclaration of {declaration.name} at {declaration.line}:{declaration.column}")

    def _declare_function(self, declaration: FunctionDef) -> None:
        return_type = declaration.return_type.name if declaration.return_type else "error"
        params = [parameter.type_node.name for parameter in declaration.params if parameter.type_node is not None]
        symbol = Symbol(
            declaration.name,
            "function",
            return_type,
            self.symbols.level,
            params=params,
            line=declaration.line,
            column=declaration.column,
        )
        if not self.symbols.define(symbol):
            self.errors.append(f"Redeclaration of function {declaration.name} at {declaration.line}:{declaration.column}")

    def _analyze_var_decl(self, declaration: VarDecl) -> None:
        self._declare_variable(declaration)

    def _analyze_function(self, declaration: FunctionDef) -> None:
        function_symbol = self.symbols.resolve(declaration.name)
        if function_symbol is None:
            return
        self.current_function = function_symbol
        self.symbols.push()
        for parameter in declaration.params:
            type_name = parameter.type_node.name if parameter.type_node else "error"
            symbol = Symbol(parameter.name, "param", type_name, self.symbols.level, line=parameter.line, column=parameter.column)
            if not self.symbols.define(symbol):
                self.errors.append(f"Duplicate parameter {parameter.name} at {parameter.line}:{parameter.column}")
        if declaration.body is not None:
            self._visit_block(declaration.body, create_scope=False)
        self.symbols.pop()
        self.current_function = None

    def _visit_block(self, block: Block, create_scope: bool = True) -> None:
        if create_scope:
            self.symbols.push()
        for statement in block.statements:
            self._visit_statement(statement)
        if create_scope:
            self.symbols.pop()

    def _visit_statement(self, statement: object) -> None:
        if isinstance(statement, Block):
            self._visit_block(statement)
        elif isinstance(statement, VarDecl):
            self._declare_variable(statement)
        elif isinstance(statement, Assignment):
            self._visit_assignment(statement)
        elif isinstance(statement, ExpressionStatement):
            self._expr_type(statement.expression)
        elif isinstance(statement, IfStatement):
            self._visit_if(statement)
        elif isinstance(statement, WhileStatement):
            self._visit_while(statement)
        elif isinstance(statement, ForStatement):
            self._visit_for(statement)
        elif isinstance(statement, ReturnStatement):
            self._visit_return(statement)
        elif isinstance(statement, InputStatement):
            self._visit_input(statement)
        elif isinstance(statement, OutputStatement):
            self._expr_type(statement.value)
        elif isinstance(statement, FunctionDef):
            self.errors.append(f"Nested function definition is not allowed at {statement.line}:{statement.column}")

    def _visit_assignment(self, statement: Assignment) -> None:
        target = self.symbols.resolve(statement.target.name if statement.target else "")
        if target is None:
            self.errors.append(f"Use of undeclared identifier {statement.target.name if statement.target else ''} at {statement.line}:{statement.column}")
            return
        if target.kind == "function":
            self.errors.append(f"Cannot assign to function name {target.name} at {statement.line}:{statement.column}")
            return
        value_type = self._expr_type(statement.value)
        if not self._compatible(target.type_name, value_type):
            self.errors.append(
                f"Type mismatch in assignment to {target.name} at {statement.line}:{statement.column}: expected {target.type_name}, got {value_type}"
            )

    def _visit_if(self, statement: IfStatement) -> None:
        self._ensure_condition(statement.condition, statement.line, statement.column)
        self._visit_statement(statement.then_branch)
        if statement.else_branch is not None:
            self._visit_statement(statement.else_branch)

    def _visit_while(self, statement: WhileStatement) -> None:
        self._ensure_condition(statement.condition, statement.line, statement.column)
        self._visit_statement(statement.body)

    def _visit_for(self, statement: ForStatement) -> None:
        self.symbols.push()
        if isinstance(statement.init, VarDecl):
            self._declare_variable(statement.init)
        elif statement.init is not None:
            self._visit_statement(statement.init)
        self._ensure_condition(statement.condition, statement.line, statement.column)
        if statement.update is not None:
            self._expr_type(statement.update)
        self._visit_statement(statement.body)
        self.symbols.pop()

    def _visit_return(self, statement: ReturnStatement) -> None:
        if self.current_function is None:
            self.errors.append(f"return used outside a function at {statement.line}:{statement.column}")
            return
        expected = self.current_function.type_name
        if expected == TYPE_EMPTY:
            if statement.value is not None:
                self.errors.append(f"Void function {self.current_function.name} should not return a value at {statement.line}:{statement.column}")
            return
        if statement.value is None:
            self.errors.append(f"Non-void function {self.current_function.name} must return a value at {statement.line}:{statement.column}")
            return
        actual = self._expr_type(statement.value)
        if not self._compatible(expected, actual):
            self.errors.append(
                f"Return type mismatch in {self.current_function.name} at {statement.line}:{statement.column}: expected {expected}, got {actual}"
            )

    def _visit_input(self, statement: InputStatement) -> None:
        target = self.symbols.resolve(statement.target.name if statement.target else "")
        if target is None:
            self.errors.append(f"Use of undeclared identifier {statement.target.name if statement.target else ''} at {statement.line}:{statement.column}")
            return
        if target.kind == "function":
            self.errors.append(f"Cannot read into function name {target.name} at {statement.line}:{statement.column}")

    def _ensure_condition(self, condition: object, line: int, column: int) -> None:
        condition_type = self._expr_type(condition)
        if condition_type not in SCALAR_TYPES:
            self.errors.append(f"Invalid condition type {condition_type} at {line}:{column}")

    def _expr_type(self, expression: object) -> str:
        if expression is None:
            return "void"
        if isinstance(expression, Literal):
            value = expression.value
            if isinstance(value, bool):
                return TYPE_FLAG
            if isinstance(value, int):
                return TYPE_WHOLE
            if isinstance(value, float):
                return TYPE_REAL
            return "error"
        if isinstance(expression, Identifier):
            symbol = self.symbols.resolve(expression.name)
            if symbol is None:
                self.errors.append(f"Use of undeclared identifier {expression.name} at {expression.line}:{expression.column}")
                return "error"
            return symbol.type_name
        if isinstance(expression, UnaryOp):
            operand_type = self._expr_type(expression.operand)
            if expression.operator == "!":
                if operand_type != TYPE_FLAG:
                    self.errors.append(f"Logical not requires bool at {expression.line}:{expression.column}")
                return TYPE_FLAG
            if operand_type not in NUMERIC_TYPES:
                self.errors.append(f"Unary minus requires numeric operand at {expression.line}:{expression.column}")
                return "error"
            return operand_type
        if isinstance(expression, BinaryOp):
            left_type = self._expr_type(expression.left)
            right_type = self._expr_type(expression.right)
            return self._binary_type(expression, left_type, right_type)
        if isinstance(expression, Call):
            symbol = self.symbols.resolve(expression.callee)
            if symbol is None:
                self.errors.append(f"Call to undeclared function {expression.callee} at {expression.line}:{expression.column}")
                return "error"
            if symbol.kind != "function":
                self.errors.append(f"{expression.callee} is not a function at {expression.line}:{expression.column}")
                return "error"
            if len(expression.args) != len(symbol.params):
                self.errors.append(
                    f"Argument count mismatch in call to {expression.callee} at {expression.line}:{expression.column}: "
                    f"expected {len(symbol.params)}, got {len(expression.args)}"
                )
            for index, arg in enumerate(expression.args):
                arg_type = self._expr_type(arg)
                if index < len(symbol.params) and not self._compatible(symbol.params[index], arg_type):
                    self.errors.append(
                        f"Argument {index + 1} type mismatch in call to {expression.callee} at {expression.line}:{expression.column}: "
                        f"expected {symbol.params[index]}, got {arg_type}"
                    )
            return symbol.type_name
        if isinstance(expression, Assignment):
            self._visit_assignment(expression)
            target = self.symbols.resolve(expression.target.name if expression.target else "")
            return target.type_name if target is not None else "error"
        if isinstance(expression, ExpressionStatement):
            return self._expr_type(expression.expression)
        return "error"

    def _binary_type(self, expression: BinaryOp, left_type: str, right_type: str) -> str:
        op = expression.operator
        if op in {"+", "-", "*", "/"}:
            if left_type not in NUMERIC_TYPES or right_type not in NUMERIC_TYPES:
                self.errors.append(f"Operator {op} requires numeric operands at {expression.line}:{expression.column}")
                return "error"
            return TYPE_REAL if TYPE_REAL in {left_type, right_type} else TYPE_WHOLE
        if op == "%":
            if left_type != TYPE_WHOLE or right_type != TYPE_WHOLE:
                self.errors.append(f"Operator % requires int operands at {expression.line}:{expression.column}")
                return "error"
            return TYPE_WHOLE
        if op in {"<", "<=", ">", ">="}:
            if left_type not in NUMERIC_TYPES or right_type not in NUMERIC_TYPES:
                self.errors.append(f"Relational operator {op} requires numeric operands at {expression.line}:{expression.column}")
            return TYPE_FLAG
        if op in {"==", "!="}:
            if not self._compatible(left_type, right_type) and not self._compatible(right_type, left_type):
                self.errors.append(f"Equality operator {op} used with incompatible types at {expression.line}:{expression.column}")
            return TYPE_FLAG
        if op in {"&&", "||"}:
            if left_type != TYPE_FLAG or right_type != TYPE_FLAG:
                self.errors.append(f"Logical operator {op} requires bool operands at {expression.line}:{expression.column}")
            return TYPE_FLAG
        return "error"

    def _compatible(self, target_type: str, source_type: str) -> bool:
        if target_type == source_type:
            return True
        if target_type == TYPE_REAL and source_type == TYPE_WHOLE:
            return True
        if target_type == TYPE_FLAG or source_type == TYPE_FLAG:
            return False
        return False
