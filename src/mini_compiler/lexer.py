from __future__ import annotations

from dataclasses import dataclass

from .errors import LexerError
from .token import Token, TokenType
from .zht_spec import BOOL_FALSE, BOOL_TRUE, KEYWORDS, TYPE_KEYWORDS

SINGLE_CHAR_TOKENS = {
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
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
}

MULTI_CHAR_TOKENS = {
    "==": TokenType.EQ,
    "!=": TokenType.NEQ,
    "<=": TokenType.LTE,
    ">=": TokenType.GTE,
    "&&": TokenType.AND,
    "||": TokenType.OR,
}


@dataclass(slots=True)
class LexerState:
    source: str
    index: int = 0
    line: int = 1
    column: int = 1


class Lexer:
    def __init__(self, source: str) -> None:
        self.state = LexerState(source=source)
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self._at_end():
            char = self._peek()
            if char in " \r\t":
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
            if char.isalpha() or char == "_":
                self.tokens.append(self._identifier_or_keyword())
                continue
            if char.isdigit():
                self.tokens.append(self._number())
                continue

            two_char = char + self._peek_next()
            if two_char in MULTI_CHAR_TOKENS:
                token = Token(MULTI_CHAR_TOKENS[two_char], two_char, self.state.line, self.state.column)
                self._advance()
                self._advance()
                self.tokens.append(token)
                continue

            if char in SINGLE_CHAR_TOKENS:
                token = Token(SINGLE_CHAR_TOKENS[char], char, self.state.line, self.state.column)
                self._advance()
                self.tokens.append(token)
                continue

            raise LexerError(f"Unexpected character {char!r} at {self.state.line}:{self.state.column}")

        self.tokens.append(Token(TokenType.EOF, "", self.state.line, self.state.column))
        return self.tokens

    def _at_end(self) -> bool:
        return self.state.index >= len(self.state.source)

    def _peek(self) -> str:
        if self._at_end():
            return "\0"
        return self.state.source[self.state.index]

    def _peek_next(self) -> str:
        next_index = self.state.index + 1
        if next_index >= len(self.state.source):
            return "\0"
        return self.state.source[next_index]

    def _advance(self) -> str:
        char = self.state.source[self.state.index]
        self.state.index += 1
        self.state.column += 1
        return char

    def _newline(self) -> None:
        self.state.index += 1
        self.state.line += 1
        self.state.column = 1

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
            if self._peek() == "\n":
                self._newline()
            else:
                self._advance()
        raise LexerError("Unterminated block comment")

    def _identifier_or_keyword(self) -> Token:
        start_index = self.state.index
        line = self.state.line
        column = self.state.column
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        lexeme = self.state.source[start_index:self.state.index]
        if lexeme in TYPE_KEYWORDS:
            return Token(TokenType.TYPE, lexeme, line, column, lexeme)
        if lexeme == BOOL_TRUE:
            return Token(TokenType.BOOL_LITERAL, lexeme, line, column, True)
        if lexeme == BOOL_FALSE:
            return Token(TokenType.BOOL_LITERAL, lexeme, line, column, False)
        if lexeme in KEYWORDS:
            return Token(TokenType.KEYWORD, lexeme, line, column, lexeme)
        return Token(TokenType.IDENTIFIER, lexeme, line, column, lexeme)

    def _number(self) -> Token:
        start_index = self.state.index
        line = self.state.line
        column = self.state.column
        while not self._at_end() and self._peek().isdigit():
            self._advance()
        is_float = False
        if not self._at_end() and self._peek() == "." and self._peek_next().isdigit():
            is_float = True
            self._advance()
            while not self._at_end() and self._peek().isdigit():
                self._advance()
        lexeme = self.state.source[start_index:self.state.index]
        if is_float:
            return Token(TokenType.FLOAT_LITERAL, lexeme, line, column, float(lexeme))
        return Token(TokenType.INT_LITERAL, lexeme, line, column, int(lexeme))
