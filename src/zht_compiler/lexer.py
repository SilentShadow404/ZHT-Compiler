from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import LexerError
from .token import Token, TokenType


_TYPE_KEYWORDS: dict[str, TokenType] = {
    "whole": TokenType.WHOLE,
    "real": TokenType.REAL,
    "letter": TokenType.LETTER,
    "text": TokenType.TEXT,
    "flag": TokenType.FLAG,
    "empty": TokenType.EMPTY,
}

_KEYWORDS: dict[str, TokenType] = {
    "when": TokenType.WHEN,
    "otherwise": TokenType.OTHERWISE,
    "choose": TokenType.CHOOSE,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    "loop": TokenType.LOOP,
    "range": TokenType.RANGE,
    "break": TokenType.BREAK,
    "skip": TokenType.SKIP,
    "give": TokenType.GIVE,
    "scan": TokenType.SCAN,
    "show": TokenType.SHOW,
    "yes": TokenType.YES,
    "no": TokenType.NO,
}

_SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "=": TokenType.ASSIGN,
    "<": TokenType.LT,
    ">": TokenType.GT,
    "!": TokenType.NOT,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
    ":": TokenType.COLON,
}

_MULTI_CHAR_TOKENS: dict[str, TokenType] = {
    "==": TokenType.EQ,
    "!=": TokenType.NEQ,
    "<=": TokenType.LTE,
    ">=": TokenType.GTE,
    "&&": TokenType.AND,
    "||": TokenType.OR,
}

_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


@dataclass(slots=True)
class _Cursor:
    source: str
    index: int = 0
    line: int = 1
    column: int = 1


class Lexer:
    def __init__(self, source: str) -> None:
        self._cursor = _Cursor(source=source)
        self._tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self._at_end():
            char = self._peek()

            if char in " \t\r":
                self._advance()
                continue
            if char == "\n":
                self._newline()
                continue

            if char == "/" and self._peek_next() == "/":
                self._skip_line_comment()
                continue
            if char == "/" and self._peek_next() == "*":
                self._skip_block_comment()
                continue

            two_char = char + self._peek_next()
            if two_char in _MULTI_CHAR_TOKENS:
                self._tokens.append(self._make_token(_MULTI_CHAR_TOKENS[two_char], two_char))
                self._advance()
                self._advance()
                continue

            if char in _SINGLE_CHAR_TOKENS:
                self._tokens.append(self._make_token(_SINGLE_CHAR_TOKENS[char], char))
                self._advance()
                continue

            if char == '"':
                self._tokens.append(self._string_literal())
                continue

            if char == "'":
                self._tokens.append(self._char_literal())
                continue

            if char.isdigit():
                self._tokens.append(self._number_literal())
                continue

            if char.isalpha() or char == "_":
                self._tokens.append(self._identifier_or_keyword())
                continue

            raise LexerError(
                f"Unexpected character {char!r} at line {self._cursor.line}, column {self._cursor.column}"
            )

        self._tokens.append(self._make_token(TokenType.EOF, ""))
        return self._tokens

    def _at_end(self) -> bool:
        return self._cursor.index >= len(self._cursor.source)

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self._cursor.source[self._cursor.index]

    def _peek_next(self) -> str:
        next_index = self._cursor.index + 1
        if next_index >= len(self._cursor.source):
            return "\0"
        return self._cursor.source[next_index]

    def _advance(self) -> str:
        char = self._cursor.source[self._cursor.index]
        self._cursor.index += 1
        if char == "\n":
            self._cursor.line += 1
            self._cursor.column = 1
        else:
            self._cursor.column += 1
        return char

    def _newline(self) -> None:
        self._advance()

    def _make_token(self, token_type: TokenType, lexeme: str, literal: object | None = None) -> Token:
        return Token(token_type, lexeme, self._cursor.line, self._cursor.column, literal)

    def _skip_line_comment(self) -> None:
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self) -> None:
        self._advance()
        self._advance()
        while not self._at_end():
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                return
            self._advance()
        raise LexerError("Unterminated block comment")

    def _identifier_or_keyword(self) -> Token:
        start_index = self._cursor.index
        start_line = self._cursor.line
        start_column = self._cursor.column

        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()

        lexeme = self._cursor.source[start_index:self._cursor.index]
        token_type = _TYPE_KEYWORDS.get(lexeme) or _KEYWORDS.get(lexeme) or TokenType.IDENTIFIER

        if token_type == TokenType.YES:
            literal: object | None = True
            token_type = TokenType.BOOL_LITERAL
        elif token_type == TokenType.NO:
            literal = False
            token_type = TokenType.BOOL_LITERAL
        elif token_type in _TYPE_KEYWORDS.values():
            literal = lexeme
        elif token_type in _KEYWORDS.values():
            literal = lexeme
        else:
            literal = lexeme

        return Token(token_type, lexeme, start_line, start_column, literal)

    def _number_literal(self) -> Token:
        start_index = self._cursor.index
        start_line = self._cursor.line
        start_column = self._cursor.column

        match = _NUMBER_RE.match(self._cursor.source, self._cursor.index)
        if not match:
            raise LexerError(f"Invalid numeric literal at line {start_line}, column {start_column}")

        lexeme = match.group(0)
        for _ in lexeme:
            self._advance()

        if "." in lexeme:
            literal: object | None = float(lexeme)
            token_type = TokenType.FLOAT_LITERAL
        else:
            literal = int(lexeme)
            token_type = TokenType.INT_LITERAL

        return Token(token_type, lexeme, start_line, start_column, literal)

    def _string_literal(self) -> Token:
        start_line = self._cursor.line
        start_column = self._cursor.column
        self._advance()

        raw_chars: list[str] = []
        while not self._at_end():
            char = self._peek()
            if char == '"':
                self._advance()
                lexeme = '"' + ''.join(raw_chars) + '"'
                literal = self._decode_escape_sequences(''.join(raw_chars), start_line, start_column)
                return Token(TokenType.STRING_LITERAL, lexeme, start_line, start_column, literal)
            if char == "\n":
                raise LexerError(f"Unterminated string literal at line {start_line}, column {start_column}")
            raw_chars.append(self._advance())

        raise LexerError(f"Unterminated string literal at line {start_line}, column {start_column}")

    def _char_literal(self) -> Token:
        start_line = self._cursor.line
        start_column = self._cursor.column
        self._advance()

        raw_chars: list[str] = []
        while not self._at_end():
            char = self._peek()
            if char == "'":
                self._advance()
                raw_value = ''.join(raw_chars)
                literal = self._decode_escape_sequences(raw_value, start_line, start_column)
                if len(literal) != 1:
                    raise LexerError(
                        f"Character literal must contain exactly one character at line {start_line}, column {start_column}"
                    )
                lexeme = "'" + raw_value + "'"
                return Token(TokenType.CHAR_LITERAL, lexeme, start_line, start_column, literal)
            if char == "\n":
                raise LexerError(f"Unterminated character literal at line {start_line}, column {start_column}")
            raw_chars.append(self._advance())

        raise LexerError(f"Unterminated character literal at line {start_line}, column {start_column}")

    @staticmethod
    def _decode_escape_sequences(text: str, line: int, column: int) -> str:
        try:
            return bytes(text, "utf-8").decode("unicode_escape")
        except UnicodeDecodeError as exc:
            raise LexerError(f"Invalid escape sequence at line {line}, column {column}") from exc
