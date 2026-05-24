from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any


def _indent(text: str, level: int = 1) -> str:
    prefix = "  " * level
    return "\n".join(prefix + line for line in text.splitlines())


@dataclass
class Node:
    def pretty(self, level: int = 0) -> str:  # type: ignore[override]
        cls = type(self).__name__
        lines = [cls]
        for k, v in self.__dict__.items():
            if isinstance(v, Node):
                lines.append(f"  {k}:")
                lines.append(_indent(v.pretty(level + 1), 1))
            elif isinstance(v, list):
                lines.append(f"  {k}:")
                for item in v:
                    if isinstance(item, Node):
                        lines.append(_indent(item.pretty(level + 1), 1))
                    elif isinstance(item, tuple):
                        for part in item:
                            if isinstance(part, Node):
                                lines.append(_indent(part.pretty(level + 1), 1))
                    else:
                        lines.append(f"    {item!r}")
            else:
                lines.append(f"  {k} = {v!r}")
        return "\n".join(lines)


@dataclass
class Program(Node):
    declarations: List[Node] = field(default_factory=list)


@dataclass
class VarDecl(Node):
    typ: str
    name: str
    size: Optional[int] = None  # for arrays
    init: Optional[Any] = None


@dataclass
class FuncDecl(Node):
    ret_type: str
    name: str
    params: List[VarDecl]
    body: 'Block'


@dataclass
class Block(Node):
    statements: List[Node] = field(default_factory=list)


@dataclass
class When(Node):
    cond: Any
    then_block: Block
    else_block: Optional[Block] = None


@dataclass
class Choose(Node):
    expr: Any
    cases: List[tuple]  # list of (value, Block)
    default: Optional[Block] = None


@dataclass
class While(Node):
    cond: Any
    body: Block


@dataclass
class RangeLoop(Node):
    init: Optional[Node]
    cond: Optional[Any]
    step: Optional[Node]
    body: Block


@dataclass
class Break(Node):
    pass


@dataclass
class Skip(Node):
    pass


@dataclass
class Give(Node):
    expr: Optional[Any]


@dataclass
class Scan(Node):
    var: Any


@dataclass
class Show(Node):
    expr: Any


@dataclass
class Assign(Node):
    target: Any
    value: Any


@dataclass
class Binary(Node):
    op: str
    left: Any
    right: Any


@dataclass
class Unary(Node):
    op: str
    operand: Any


@dataclass
class Literal(Node):
    value: Any
    typ: Optional[str] = None


@dataclass
class VarRef(Node):
    name: str


@dataclass
class ArrayAccess(Node):
    name: str
    index: Any


@dataclass
class FuncCall(Node):
    name: str
    args: List[Any]
