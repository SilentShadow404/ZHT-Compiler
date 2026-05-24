from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    EOF = auto()
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    CHAR_LITERAL = auto()
    BOOL_LITERAL = auto()

    WHOLE = auto()
    REAL = auto()
    LETTER = auto()
    TEXT = auto()
    FLAG = auto()
    EMPTY = auto()

    WHEN = auto()
    OTHERWISE = auto()
    CHOOSE = auto()
    CASE = auto()
    DEFAULT = auto()
    LOOP = auto()
    RANGE = auto()
    BREAK = auto()
    SKIP = auto()
    GIVE = auto()
    SCAN = auto()
    SHOW = auto()

    YES = auto()
    NO = auto()

    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    ASSIGN = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    LTE = auto()
    GT = auto()
    GTE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    COMMA = auto()
    SEMICOLON = auto()
    COLON = auto()


@dataclass(frozen=True, slots=True)
class Token:
    type: TokenType
    lexeme: str
    line: int
    column: int
    literal: object | None = None

    def __repr__(self) -> str:
        return (
            f"Token(type={self.type.name}, lexeme={self.lexeme!r}, "
            f"literal={self.literal!r}, line={self.line}, column={self.column})"
        )