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
    Parameter,
    Program,
    ReturnStatement,
    TypeNode,
    UnaryOp,
    VarDecl,
    WhileStatement,
)
from .errors import ParseError
from .token import Token, TokenType
from .zht_spec import (
    KEYWORD_GIVE,
    KEYWORD_LOOP,
    KEYWORD_OTHERWISE,
    KEYWORD_RANGE,
    KEYWORD_SCAN,
    KEYWORD_SHOW,
    KEYWORD_WHEN,
)


STATEMENT_START_KEYWORDS = {
    KEYWORD_WHEN,
    KEYWORD_OTHERWISE,
    KEYWORD_LOOP,
    KEYWORD_RANGE,
    KEYWORD_GIVE,
    KEYWORD_SCAN,
    KEYWORD_SHOW,
}


@dataclass(slots=True)
class ParserState:
    tokens: list[Token]
    current: int = 0


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.state = ParserState(tokens=tokens)
        self.errors: list[str] = []

    def parse(self) -> Program:
        declarations: list[object] = []
        while not self._check(TokenType.EOF):
            try:
                declarations.append(self._declaration_or_function())
            except ParseError as exc:
                self.errors.append(str(exc))
                self._synchronize()
        eof = self._peek()
        return Program(eof.line, eof.column, declarations)

    def _declaration_or_function(self) -> object:
        type_node = self._parse_type()
        name = self._consume(TokenType.IDENTIFIER, "Expected identifier after type")
        if self._match(TokenType.LPAREN):
            params = self._parse_parameters()
            body = self._parse_block()
            return FunctionDef(type_node.line, type_node.column, type_node, name.lexeme, params, body)
        initializer = None
        if self._match(TokenType.ASSIGN):
            initializer = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDecl(type_node.line, type_node.column, type_node, name.lexeme, initializer)

    def _parse_type(self) -> TypeNode:
        token = self._consume(TokenType.TYPE, "Expected type specifier")
        return TypeNode(token.line, token.column, token.lexeme)

    def _parse_parameters(self) -> list[Parameter]:
        params: list[Parameter] = []
        if self._check(TokenType.RPAREN):
            self._advance()
            return params
        while True:
            type_node = self._parse_type()
            name = self._consume(TokenType.IDENTIFIER, "Expected parameter name")
            params.append(Parameter(type_node.line, type_node.column, type_node, name.lexeme))
            if not self._match(TokenType.COMMA):
                break
        self._consume(TokenType.RPAREN, "Expected ')' after parameter list")
        return params

    def _parse_block(self) -> Block:
        left = self._consume(TokenType.LBRACE, "Expected '{' to start block")
        statements: list[object] = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            statements.append(self._statement())
        self._consume(TokenType.RBRACE, "Expected '}' to end block")
        return Block(left.line, left.column, statements)

    def _statement(self) -> object:
        if self._match(TokenType.LBRACE):
            self._step_back()
            return self._parse_block()
        if self._match_keyword(KEYWORD_WHEN):
            return self._if_statement()
        if self._match_keyword(KEYWORD_LOOP):
            return self._while_statement()
        if self._match_keyword(KEYWORD_RANGE):
            return self._for_statement()
        if self._match_keyword(KEYWORD_GIVE):
            return self._return_statement()
        if self._match_keyword(KEYWORD_SCAN):
            return self._input_statement()
        if self._match_keyword(KEYWORD_SHOW):
            return self._output_statement()
        if self._check(TokenType.TYPE):
            return self._local_declaration()
        return self._expression_or_assignment_statement()

    def _local_declaration(self) -> VarDecl:
        type_node = self._parse_type()
        name = self._consume(TokenType.IDENTIFIER, "Expected identifier after type")
        initializer = None
        if self._match(TokenType.ASSIGN):
            initializer = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarDecl(type_node.line, type_node.column, type_node, name.lexeme, initializer)

    def _if_statement(self) -> IfStatement:
        keyword = self._previous()
        self._consume(TokenType.LPAREN, "Expected '(' after when")
        condition = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')' after when condition")
        then_branch = self._statement()
        else_branch = None
        if self._match_keyword(KEYWORD_OTHERWISE):
            else_branch = self._statement()
        return IfStatement(keyword.line, keyword.column, condition, then_branch, else_branch)

    def _while_statement(self) -> WhileStatement:
        keyword = self._previous()
        self._consume(TokenType.LPAREN, "Expected '(' after loop")
        condition = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')' after loop condition")
        body = self._statement()
        return WhileStatement(keyword.line, keyword.column, condition, body)

    def _for_statement(self) -> ForStatement:
        keyword = self._previous()
        self._consume(TokenType.LPAREN, "Expected '(' after range")
        init = None
        if not self._check(TokenType.SEMICOLON):
            if self._check(TokenType.TYPE):
                init = self._for_init_declaration()
            else:
                init = self._expression_or_assignment_statement(expect_semicolon=False)
        self._consume(TokenType.SEMICOLON, "Expected ';' after range initializer")
        condition = None
        if not self._check(TokenType.SEMICOLON):
            condition = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after range condition")
        update = None
        if not self._check(TokenType.RPAREN):
            update = self._expression_or_assignment_statement(expect_semicolon=False)
        self._consume(TokenType.RPAREN, "Expected ')' after range clauses")
        body = self._statement()
        return ForStatement(keyword.line, keyword.column, init, condition, update, body)

    def _for_init_declaration(self) -> VarDecl:
        type_node = self._parse_type()
        name = self._consume(TokenType.IDENTIFIER, "Expected identifier after type")
        initializer = None
        if self._match(TokenType.ASSIGN):
            initializer = self._expression()
        return VarDecl(type_node.line, type_node.column, type_node, name.lexeme, initializer)

    def _return_statement(self) -> ReturnStatement:
        keyword = self._previous()
        value = None
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after give value")
        return ReturnStatement(keyword.line, keyword.column, value)

    def _input_statement(self) -> InputStatement:
        keyword = self._previous()
        self._consume(TokenType.LPAREN, "Expected '(' after scan")
        name = self._consume(TokenType.IDENTIFIER, "Expected identifier in scan statement")
        self._consume(TokenType.RPAREN, "Expected ')' after scan target")
        self._consume(TokenType.SEMICOLON, "Expected ';' after scan statement")
        return InputStatement(keyword.line, keyword.column, Identifier(name.line, name.column, name.lexeme))

    def _output_statement(self) -> OutputStatement:
        keyword = self._previous()
        self._consume(TokenType.LPAREN, "Expected '(' after show")
        value = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')' after show value")
        self._consume(TokenType.SEMICOLON, "Expected ';' after show statement")
        return OutputStatement(keyword.line, keyword.column, value)

    def _expression_or_assignment_statement(self, expect_semicolon: bool = True) -> object:
        if self._check(TokenType.IDENTIFIER) and self._check_next(TokenType.ASSIGN):
            name = self._advance()
            self._advance()
            value = self._expression()
            if expect_semicolon:
                self._consume(TokenType.SEMICOLON, "Expected ';' after assignment")
            return Assignment(name.line, name.column, Identifier(name.line, name.column, name.lexeme), value)
        expr = self._expression()
        if expect_semicolon:
            self._consume(TokenType.SEMICOLON, "Expected ';' after expression")
            return ExpressionStatement(expr.line, expr.column, expr)
        return expr

    def _expression(self) -> object:
        return self._or()

    def _or(self) -> object:
        expr = self._and()
        while self._match(TokenType.OR):
            operator = self._previous()
            right = self._and()
            expr = BinaryOp(operator.line, operator.column, expr, operator.lexeme, right)
        return expr

    def _and(self) -> object:
        expr = self._equality()
        while self._match(TokenType.AND):
            operator = self._previous()
            right = self._equality()
            expr = BinaryOp(operator.line, operator.column, expr, operator.lexeme, right)
        return expr

    def _equality(self) -> object:
        expr = self._comparison()
        while self._match(TokenType.EQ, TokenType.NEQ):
            operator = self._previous()
            right = self._comparison()
            expr = BinaryOp(operator.line, operator.column, expr, operator.lexeme, right)
        return expr

    def _comparison(self) -> object:
        expr = self._term()
        while self._match(TokenType.LT, TokenType.LTE, TokenType.GT, TokenType.GTE):
            operator = self._previous()
            right = self._term()
            expr = BinaryOp(operator.line, operator.column, expr, operator.lexeme, right)
        return expr

    def _term(self) -> object:
        expr = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous()
            right = self._factor()
            expr = BinaryOp(operator.line, operator.column, expr, operator.lexeme, right)
        return expr

    def _factor(self) -> object:
        expr = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            operator = self._previous()
            right = self._unary()
            expr = BinaryOp(operator.line, operator.column, expr, operator.lexeme, right)
        return expr

    def _unary(self) -> object:
        if self._match(TokenType.NOT, TokenType.MINUS):
            operator = self._previous()
            operand = self._unary()
            return UnaryOp(operator.line, operator.column, operator.lexeme, operand)
        return self._primary()

    def _primary(self) -> object:
        if self._match(TokenType.INT_LITERAL, TokenType.FLOAT_LITERAL, TokenType.BOOL_LITERAL):
            token = self._previous()
            return Literal(token.line, token.column, token.literal, token.lexeme)
        if self._match(TokenType.IDENTIFIER):
            name = self._previous()
            if self._match(TokenType.LPAREN):
                args: list[object] = []
                if not self._check(TokenType.RPAREN):
                    while True:
                        args.append(self._expression())
                        if not self._match(TokenType.COMMA):
                            break
                self._consume(TokenType.RPAREN, "Expected ')' after arguments")
                return Call(name.line, name.column, name.lexeme, args)
            return Identifier(name.line, name.column, name.lexeme)
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._consume(TokenType.RPAREN, "Expected ')' after expression")
            return expr
        token = self._peek()
        raise ParseError(f"Unexpected token {token.lexeme!r} at {token.line}:{token.column}")

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()
        token = self._peek()
        raise ParseError(f"{message} at {token.line}:{token.column}")

    def _match(self, *token_types: TokenType) -> bool:
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _match_keyword(self, keyword: str) -> bool:
        if self._check(TokenType.KEYWORD) and self._peek().lexeme == keyword:
            self._advance()
            return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        return self._peek().type == token_type

    def _check_next(self, token_type: TokenType) -> bool:
        if self.state.current + 1 >= len(self.state.tokens):
            return False
        return self.state.tokens[self.state.current + 1].type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.state.current += 1
        return self._previous()

    def _previous(self) -> Token:
        return self.state.tokens[self.state.current - 1]

    def _peek(self) -> Token:
        return self.state.tokens[self.state.current]

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _synchronize(self) -> None:
        self._advance()
        while not self._is_at_end():
            if self._previous().type == TokenType.SEMICOLON:
                return
            if self._peek().type == TokenType.KEYWORD and self._peek().lexeme in STATEMENT_START_KEYWORDS:
                return
            if self._peek().type == TokenType.TYPE:
                return
            if self._peek().type == TokenType.RBRACE:
                return
            self._advance()

    def _step_back(self) -> None:
        if self.state.current > 0:
            self.state.current -= 1
