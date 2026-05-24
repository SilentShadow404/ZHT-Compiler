from __future__ import annotations

from typing import Dict, List, Optional

from .ast import (
    ArrayAccess, Assign, Binary, Block, Break, Choose, FuncCall,
    FuncDecl, Give, Literal, Node, Program, RangeLoop, Scan, Show,
    Skip, Unary, VarDecl, VarRef, When, While,
)

_NUMERIC = {"whole", "real"}
_COMPATIBLE_PAIRS: Dict[frozenset, str] = {
    frozenset({"whole", "whole"}): "whole",
    frozenset({"real",  "real"}):  "real",
    frozenset({"whole", "real"}):  "real",
}


class Symbol:
    def __init__(self, name: str, typ: str, size: Optional[int] = None, is_func: bool = False):
        self.name = name
        self.typ = typ
        self.size = size
        self.is_func = is_func
        self.param_types: List[str] = []
        self.ret_type: str = "empty"

    def __repr__(self) -> str:
        if self.is_func:
            params = ", ".join(self.param_types)
            return f"func({params}) -> {self.ret_type}"
        arr = f"[{self.size}]" if self.size else ""
        return f"{self.typ}{arr}"


class Scope:
    def __init__(self, parent: Optional[Scope] = None, func_ret_type: str = "empty"):
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.func_ret_type = func_ret_type

    def define(self, sym: Symbol) -> None:
        self.symbols[sym.name] = sym

    def resolve(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def enclosing_ret_type(self) -> str:
        if self.func_ret_type != "empty":
            return self.func_ret_type
        if self.parent:
            return self.parent.enclosing_ret_type()
        return "empty"


class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.global_scope: Scope = Scope()
        self.errors: List[str] = []

    # ---------------------------------------------------------------
    # Public entry
    # ---------------------------------------------------------------

    def analyze(self, program: Program) -> None:
        # Pass 1: register function signatures
        for d in program.declarations:
            if isinstance(d, FuncDecl):
                self._register_func(d)
        # Pass 2: top-level variable declarations
        for d in program.declarations:
            if isinstance(d, VarDecl):
                self._declare_var(d, self.global_scope)
        # Pass 3: type-check function bodies
        for d in program.declarations:
            if isinstance(d, FuncDecl):
                self._check_func(d)

    # ---------------------------------------------------------------
    # Registration
    # ---------------------------------------------------------------

    def _register_func(self, func: FuncDecl) -> None:
        if self.global_scope.resolve(func.name):
            self._err(f"Redeclaration of '{func.name}'")
            return
        sym = Symbol(func.name, "func", is_func=True)
        sym.ret_type = func.ret_type
        sym.param_types = [p.typ for p in func.params]
        self.global_scope.define(sym)

    def _declare_var(self, decl: VarDecl, scope: Scope) -> None:
        existing = scope.symbols.get(decl.name)
        if existing:
            self._err(f"Redeclaration of '{decl.name}'")
        sym = Symbol(decl.name, decl.typ, decl.size)
        scope.define(sym)
        if decl.init is not None:
            init_t = self._expr_type(decl.init, scope)
            if init_t and not self._assignable(decl.typ, init_t):
                self._err(
                    f"Type mismatch: cannot assign '{init_t}' to "
                    f"'{decl.typ}' variable '{decl.name}'"
                )

    # ---------------------------------------------------------------
    # Function body
    # ---------------------------------------------------------------

    def _check_func(self, func: FuncDecl) -> None:
        scope = Scope(parent=self.global_scope, func_ret_type=func.ret_type)
        for p in func.params:
            scope.define(Symbol(p.name, p.typ))
        self._check_block(func.body, scope)

    def _check_block(self, block: Block, scope: Scope) -> None:
        for stmt in block.statements:
            self._check_stmt(stmt, scope)

    # ---------------------------------------------------------------
    # Statement checking
    # ---------------------------------------------------------------

    def _check_stmt(self, stmt, scope: Scope) -> None:  # noqa: C901
        if isinstance(stmt, VarDecl):
            self._declare_var(stmt, scope)

        elif isinstance(stmt, Assign):
            if isinstance(stmt.target, VarRef):
                sym = scope.resolve(stmt.target.name)
                if not sym:
                    self._err(f"Undeclared variable '{stmt.target.name}'")
                else:
                    rhs = self._expr_type(stmt.value, scope)
                    if rhs and not self._assignable(sym.typ, rhs):
                        self._err(
                            f"Type mismatch in assignment to '{stmt.target.name}': "
                            f"expected '{sym.typ}', got '{rhs}'"
                        )
            elif isinstance(stmt.target, ArrayAccess):
                sym = scope.resolve(stmt.target.name)
                if not sym:
                    self._err(f"Undeclared array '{stmt.target.name}'")
                else:
                    if sym.size is None:
                        self._err(f"'{stmt.target.name}' is not an array")
                    self._expr_type(stmt.target.index, scope)
                    rhs = self._expr_type(stmt.value, scope)
                    if rhs and not self._assignable(sym.typ, rhs):
                        self._err(
                            f"Type mismatch in array assignment to "
                            f"'{stmt.target.name}[]': expected '{sym.typ}', got '{rhs}'"
                        )

        elif isinstance(stmt, When):
            ctype = self._expr_type(stmt.cond, scope)
            if ctype and ctype != "flag":
                self._err(f"'when' condition must be 'flag', got '{ctype}'")
            self._check_block(stmt.then_block, Scope(parent=scope))
            if stmt.else_block:
                self._check_block(stmt.else_block, Scope(parent=scope))

        elif isinstance(stmt, Choose):
            self._expr_type(stmt.expr, scope)
            for val, blk in stmt.cases:
                self._expr_type(val, scope)
                self._check_block(blk, Scope(parent=scope))
            if stmt.default:
                self._check_block(stmt.default, Scope(parent=scope))

        elif isinstance(stmt, While):
            ctype = self._expr_type(stmt.cond, scope)
            if ctype and ctype != "flag":
                self._err(f"'loop' condition must be 'flag', got '{ctype}'")
            self._check_block(stmt.body, Scope(parent=scope))

        elif isinstance(stmt, RangeLoop):
            inner = Scope(parent=scope)
            if stmt.init:
                self._check_stmt(stmt.init, inner)
            if stmt.cond:
                self._expr_type(stmt.cond, inner)
            if stmt.step:
                if isinstance(stmt.step, Assign):
                    self._check_stmt(stmt.step, inner)
                else:
                    self._expr_type(stmt.step, inner)
            self._check_block(stmt.body, inner)

        elif isinstance(stmt, Give):
            expected = scope.enclosing_ret_type()
            if stmt.expr is None:
                if expected not in ("empty", "void"):
                    self._err(f"Function must return a value of type '{expected}'")
            else:
                actual = self._expr_type(stmt.expr, scope)
                if actual and expected not in ("empty", "void") and not self._assignable(expected, actual):
                    self._err(
                        f"Return type mismatch: function returns '{expected}', got '{actual}'"
                    )

        elif isinstance(stmt, Scan):
            target = stmt.var
            if isinstance(target, VarRef):
                if not scope.resolve(target.name):
                    self._err(f"Undeclared variable '{target.name}' in scan()")
            elif isinstance(target, ArrayAccess):
                sym = scope.resolve(target.name)
                if not sym:
                    self._err(f"Undeclared array '{target.name}' in scan()")
                else:
                    self._expr_type(target.index, scope)

        elif isinstance(stmt, Show):
            self._expr_type(stmt.expr, scope)

        elif isinstance(stmt, Block):
            self._check_block(stmt, Scope(parent=scope))

        elif isinstance(stmt, (Break, Skip)):
            pass

        else:
            # expression-statement
            self._expr_type(stmt, scope)  # type: ignore[arg-type]

    # ---------------------------------------------------------------
    # Expression type inference
    # ---------------------------------------------------------------

    def _expr_type(self, expr, scope: Scope) -> Optional[str]:  # noqa: C901
        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "flag"
            if isinstance(expr.value, int):
                return "whole"
            if isinstance(expr.value, float):
                return "real"
            if isinstance(expr.value, str):
                return "text" if expr.typ == "text" else "letter"
            return expr.typ

        if isinstance(expr, VarRef):
            sym = scope.resolve(expr.name)
            if not sym:
                self._err(f"Undeclared identifier '{expr.name}'")
                return None
            return sym.typ

        if isinstance(expr, ArrayAccess):
            sym = scope.resolve(expr.name)
            if not sym:
                self._err(f"Undeclared array '{expr.name}'")
                return None
            if sym.size is None:
                self._err(f"'{expr.name}' is not an array")
            self._expr_type(expr.index, scope)
            return sym.typ

        if isinstance(expr, Binary):
            lt = self._expr_type(expr.left, scope)
            rt = self._expr_type(expr.right, scope)
            if expr.op in ("+", "-", "*", "/", "%"):
                if lt and rt:
                    key = frozenset({lt, rt})
                    result = _COMPATIBLE_PAIRS.get(key)
                    if result is None:
                        self._err(
                            f"Operator '{expr.op}' not applicable to '{lt}' and '{rt}'"
                        )
                        return None
                    return result
                return "whole"
            if expr.op in ("<", "<=", ">", ">=", "==", "!="):
                return "flag"
            if expr.op in ("&&", "||"):
                if lt and lt != "flag":
                    self._err(f"Operator '{expr.op}' requires 'flag' operands, got '{lt}'")
                if rt and rt != "flag":
                    self._err(f"Operator '{expr.op}' requires 'flag' operands, got '{rt}'")
                return "flag"

        if isinstance(expr, Unary):
            t = self._expr_type(expr.operand, scope)
            if expr.op == "!":
                if t and t != "flag":
                    self._err(f"Unary '!' requires 'flag', got '{t}'")
                return "flag"
            if expr.op == "-":
                if t and t not in _NUMERIC:
                    self._err(f"Unary '-' requires numeric type, got '{t}'")
                return t

        if isinstance(expr, FuncCall):
            sym = scope.resolve(expr.name)
            if not sym:
                self._err(f"Undeclared function '{expr.name}'")
                return None
            if not sym.is_func:
                self._err(f"'{expr.name}' is not callable")
                return None
            if len(expr.args) != len(sym.param_types):
                self._err(
                    f"Function '{expr.name}' expects {len(sym.param_types)} "
                    f"argument(s), got {len(expr.args)}"
                )
            for i, (arg, pt) in enumerate(zip(expr.args, sym.param_types)):
                at = self._expr_type(arg, scope)
                if at and not self._assignable(pt, at):
                    self._err(
                        f"Argument {i+1} of '{expr.name}': expected '{pt}', got '{at}'"
                    )
            return sym.ret_type

        return None

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    def _assignable(self, expected: str, actual: str) -> bool:
        if expected == actual:
            return True
        # numeric widening / narrowing — both allowed with warning suppressed
        if expected in _NUMERIC and actual in _NUMERIC:
            return True
        return False

    def _err(self, msg: str) -> None:
        self.errors.append(msg)

    # ---------------------------------------------------------------
    # Symbol table dump for UI
    # ---------------------------------------------------------------

    def get_symbol_table_text(self) -> str:
        lines = ["=== Global Scope ==="]
        for name, sym in self.global_scope.symbols.items():
            lines.append(f"  {name:20s}  {sym}")
        return "\n".join(lines)
