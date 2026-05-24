from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Node:
    line: int
    column: int


@dataclass(slots=True)
class Program(Node):
    declarations: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class TypeNode(Node):
    name: str = ""


@dataclass(slots=True)
class Parameter(Node):
    type_node: TypeNode | None = None
    name: str = ""


@dataclass(slots=True)
class Block(Node):
    statements: list[Any] = field(default_factory=list)


@dataclass(slots=True)
class FunctionDef(Node):
    return_type: TypeNode | None = None
    name: str = ""
    params: list[Parameter] = field(default_factory=list)
    body: Block | None = None


@dataclass(slots=True)
class VarDecl(Node):
    type_node: TypeNode | None = None
    name: str = ""
    initializer: Any | None = None


@dataclass(slots=True)
class Assignment(Node):
    target: "Identifier | None" = None
    value: Any | None = None


@dataclass(slots=True)
class ExpressionStatement(Node):
    expression: Any | None = None


@dataclass(slots=True)
class IfStatement(Node):
    condition: Any | None = None
    then_branch: Any | None = None
    else_branch: Any | None = None


@dataclass(slots=True)
class WhileStatement(Node):
    condition: Any | None = None
    body: Any | None = None


@dataclass(slots=True)
class ForStatement(Node):
    init: Any | None = None
    condition: Any | None = None
    update: Any | None = None
    body: Any | None = None


@dataclass(slots=True)
class ReturnStatement(Node):
    value: Any | None = None


@dataclass(slots=True)
class InputStatement(Node):
    target: "Identifier | None" = None


@dataclass(slots=True)
class OutputStatement(Node):
    value: Any | None = None


@dataclass(slots=True)
class Identifier(Node):
    name: str = ""


@dataclass(slots=True)
class Literal(Node):
    value: Any = None
    literal_type: str = ""


@dataclass(slots=True)
class UnaryOp(Node):
    operator: str = ""
    operand: Any | None = None


@dataclass(slots=True)
class BinaryOp(Node):
    left: Any | None = None
    operator: str = ""
    right: Any | None = None


@dataclass(slots=True)
class Call(Node):
    callee: str = ""
    args: list[Any] = field(default_factory=list)
