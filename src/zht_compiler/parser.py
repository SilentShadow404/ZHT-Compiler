from typing import List, Optional
from .token import Token, TokenType
from .ast import *


TYPE_TOKENS = {
    TokenType.WHOLE,
    TokenType.REAL,
    TokenType.LETTER,
    TokenType.TEXT,
    TokenType.FLAG,
    TokenType.EMPTY,
}

STATEMENT_KEYWORDS = {
    TokenType.WHEN,
    TokenType.OTHERWISE,
    TokenType.CHOOSE,
    TokenType.CASE,
    TokenType.DEFAULT,
    TokenType.LOOP,
    TokenType.RANGE,
    TokenType.BREAK,
    TokenType.SKIP,
    TokenType.GIVE,
    TokenType.SCAN,
    TokenType.SHOW,
}


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> Program:
        prog = Program()
        while not self._is_at_end():
            decl = self._declaration()
            if decl:
                prog.declarations.append(decl)
        return prog

    # utilities
    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self.tokens[self.current - 1]

    def _check_keyword(self, lexeme: str) -> bool:
        t = self._peek()
        return t.lexeme == lexeme and (
            t.type in TYPE_TOKENS or t.type in STATEMENT_KEYWORDS or t.type in {TokenType.YES, TokenType.NO}
        )

    def _match(self, *types) -> bool:
        if self._peek().type in types:
            self._advance()
            return True
        return False

    def _consume(self, ttype, msg):
        if self._peek().type == ttype:
            return self._advance()
        raise ParseError(msg + f" at {self._peek().line}")

    # Declarations
    def _declaration(self):
        if self._peek().type in TYPE_TOKENS:
            return self._var_or_func()
        # fallback: expression or statement
        return self._statement()

    def _var_or_func(self):
        typ = self._advance().lexeme
        name_tok = self._consume(TokenType.IDENTIFIER, "Expected identifier")
        name = name_tok.lexeme
        # array
        size = None
        if self._match(TokenType.LBRACKET):
            size_tok = self._consume(TokenType.INT_LITERAL, "Expected array size")
            size = int(size_tok.literal)
            self._consume(TokenType.RBRACKET, "Expected ']'")

        if self._match(TokenType.LPAREN):
            # function
            params = []
            if not self._match(TokenType.RPAREN):
                while True:
                    ptype_tok = self._consume_type_token("Expected parameter type")
                    pname_tok = self._consume(TokenType.IDENTIFIER, "Expected parameter name")
                    params.append(VarDecl(ptype_tok.lexeme, pname_tok.lexeme))
                    if self._match(TokenType.COMMA):
                        continue
                    self._consume(TokenType.RPAREN, "Expected ')' after params")
                    break
            body = self._block()
            return FuncDecl(typ, name, params, body)
        else:
            init = None
            if self._match(TokenType.ASSIGN):
                init = self._expression()
            self._consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
            return VarDecl(typ, name, size, init)

    # statements
    def _statement(self):
        if self._check_keyword('when'):
            return self._when()
        if self._check_keyword('choose'):
            return self._choose()
        if self._check_keyword('loop'):
            return self._while()
        if self._check_keyword('range'):
            return self._range()
        if self._check_keyword('break'):
            self._advance(); self._consume(TokenType.SEMICOLON, "Expected ';'"); return Break()
        if self._check_keyword('skip'):
            self._advance(); self._consume(TokenType.SEMICOLON, "Expected ';'"); return Skip()
        if self._check_keyword('give'):
            self._advance(); expr = None
            if not self._match(TokenType.SEMICOLON):
                expr = self._expression(); self._consume(TokenType.SEMICOLON, "Expected ';'")
            return Give(expr)
        if self._check_keyword('scan'):
            self._advance(); self._consume(TokenType.LPAREN, "Expected '(' after scan");
            target = self._var_target()
            self._consume(TokenType.RPAREN, "Expected )"); self._consume(TokenType.SEMICOLON, "Expected ;"); return Scan(target)
        if self._check_keyword('show'):
            self._advance(); self._consume(TokenType.LPAREN, "Expected '(' after show"); expr = self._expression(); self._consume(TokenType.RPAREN, "Expected )"); self._consume(TokenType.SEMICOLON, "Expected ;"); return Show(expr)
        if self._peek().type == TokenType.LBRACE:
            return self._block()
        # expression or assignment
        expr = self._expression()
        if isinstance(expr, (VarRef, ArrayAccess)) and self._match(TokenType.ASSIGN):
            val = self._expression(); self._consume(TokenType.SEMICOLON, "Expected ;"); return Assign(expr, val)
        self._consume(TokenType.SEMICOLON, "Expected ; after expression")
        return expr

    def _block(self) -> Block:
        self._consume(TokenType.LBRACE, "Expected '{'")
        stmts = []
        while not self._match(TokenType.RBRACE):
            if self._is_at_end():
                raise ParseError("Unterminated block")
            stmts.append(self._declaration())
        return Block(stmts)

    def _when(self):
        self._consume(TokenType.WHEN, "when expected")
        self._consume(TokenType.LPAREN, "Expected '('")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')'")
        then_block = self._block()
        else_block = None
        if self._check_keyword('otherwise'):
            self._advance(); else_block = self._block()
        return When(cond, then_block, else_block)

    def _choose(self):
        self._consume(TokenType.CHOOSE, "choose expected")
        self._consume(TokenType.LPAREN, "Expected '('")
        expr = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')'")
        self._consume(TokenType.LBRACE, "Expected '{'")
        cases = []
        default = None
        while not self._match(TokenType.RBRACE):
            if self._check_keyword('case'):
                self._advance(); val = self._expression(); self._consume(TokenType.COLON, "Expected ':'");
                # gather statements until next case/default or '}'
                body_stmts = []
                while not (self._check_keyword('case') or self._check_keyword('default') or self._peek().type == TokenType.RBRACE):
                    body_stmts.append(self._declaration())
                cases.append((val, Block(body_stmts)))
            elif self._check_keyword('default'):
                self._advance(); self._consume(TokenType.COLON, "Expected ':'");
                body_stmts = []
                while not (self._check_keyword('case') or self._peek().type == TokenType.RBRACE):
                    body_stmts.append(self._declaration())
                default = Block(body_stmts)
            else:
                raise ParseError("Unexpected token in choose")
        return Choose(expr, cases, default)

    def _while(self):
        self._consume(TokenType.LOOP, "loop expected")
        self._consume(TokenType.LPAREN, "Expected '('")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')'")
        body = self._block()
        return While(cond, body)

    def _range(self):
        self._consume(TokenType.RANGE, "range expected")
        self._consume(TokenType.LPAREN, "Expected '('")
        init = None
        if not self._match(TokenType.SEMICOLON):
            init = self._declaration()  # consumes its own ';'
        cond = None
        if not self._match(TokenType.SEMICOLON):
            cond = self._expression()
            self._consume(TokenType.SEMICOLON, "Expected ';' in range")
        step = None
        if not self._match(TokenType.RPAREN):
            # step is an assignment or expression (no trailing semicolon)
            expr = self._expression()
            if isinstance(expr, (VarRef, ArrayAccess)) and self._match(TokenType.ASSIGN):
                val = self._expression()
                step = Assign(expr, val)
            else:
                step = expr
            self._consume(TokenType.RPAREN, "Expected ')' in range")
        body = self._block()
        return RangeLoop(init, cond, step, body)

    def _var_target(self):
        name = self._consume(TokenType.IDENTIFIER, "Expected identifier").lexeme
        if self._match(TokenType.LBRACKET):
            idx = self._expression(); self._consume(TokenType.RBRACKET, "Expected ]"); return ArrayAccess(name, idx)
        return VarRef(name)

    def _consume_type_token(self, msg):
        if self._peek().type in TYPE_TOKENS:
            return self._advance()
        raise ParseError(msg + f" at {self._peek().line}")

    # Expressions (precedence climbing)
    def _expression(self):
        return self._or()

    def _or(self):
        node = self._and()
        while self._match(TokenType.OR):
            op = '||'
            right = self._and()
            node = Binary(op, node, right)
        return node

    def _and(self):
        node = self._equality()
        while self._match(TokenType.AND):
            op = '&&'
            right = self._equality()
            node = Binary(op, node, right)
        return node

    def _equality(self):
        node = self._comparison()
        while self._match(TokenType.EQ, TokenType.NEQ):
            op = self.tokens[self.current - 1].lexeme
            right = self._comparison()
            node = Binary(op, node, right)
        return node

    def _comparison(self):
        node = self._term()
        while self._match(TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.tokens[self.current - 1].lexeme
            right = self._term()
            node = Binary(op, node, right)
        return node

    def _term(self):
        node = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            op = self.tokens[self.current - 1].lexeme
            right = self._factor(); node = Binary(op, node, right)
        return node

    def _factor(self):
        node = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.tokens[self.current - 1].lexeme
            right = self._unary(); node = Binary(op, node, right)
        return node

    def _unary(self):
        if self._match(TokenType.NOT, TokenType.MINUS):
            op = self.tokens[self.current - 1].lexeme
            right = self._unary(); return Unary(op, right)
        return self._primary()

    def _primary(self):
        t = self._peek()
        if t.type == TokenType.INT_LITERAL:
            self._advance(); return Literal(t.literal, 'whole')
        if t.type == TokenType.FLOAT_LITERAL:
            self._advance(); return Literal(t.literal, 'real')
        if t.type == TokenType.STRING_LITERAL:
            self._advance(); return Literal(t.literal, 'text')
        if t.type == TokenType.CHAR_LITERAL:
            self._advance(); return Literal(t.literal, 'letter')
        if t.type == TokenType.IDENTIFIER:
            self._advance(); name = t.lexeme
            if self._match(TokenType.LPAREN):
                args = []
                if not self._match(TokenType.RPAREN):
                    while True:
                        args.append(self._expression())
                        if self._match(TokenType.COMMA):
                            continue
                        self._consume(TokenType.RPAREN, "Expect ')' after args")
                        break
                return FuncCall(name, args)
            if self._match(TokenType.LBRACKET):
                idx = self._expression(); self._consume(TokenType.RBRACKET, "Expect ]"); return ArrayAccess(name, idx)
            return VarRef(name)
        if t.type == TokenType.BOOL_LITERAL:
            self._advance(); return Literal(bool(t.literal), 'flag')
        if t.type == TokenType.LPAREN:
            self._advance(); expr = self._expression(); self._consume(TokenType.RPAREN, "Expect )"); return expr
        raise ParseError(f"Unexpected token {t.lexeme} at line {t.line}")
