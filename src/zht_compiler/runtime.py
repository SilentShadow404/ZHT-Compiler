"""
AST-walking interpreter for ZHT.

Design:
  - Environment is a list of dicts (stack frames); the innermost dict is searched first.
  - Control-flow uses Python exceptions: _ReturnException, _BreakException, _ContinueException.
  - scan() pops from self.inputs (list of strings already split by the UI).
  - show() appends to self.output_lines.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .ast import (
    ArrayAccess, Assign, Binary, Block, Break, Choose, FuncCall,
    FuncDecl, Give, Literal, Node, Program, RangeLoop, Scan, Show,
    Skip, Unary, VarDecl, VarRef, When, While,
)


# ---------------------------------------------------------------------------
# Control-flow signals
# ---------------------------------------------------------------------------

class _ReturnException(Exception):
    def __init__(self, value: Any = None):
        self.value = value


class _BreakException(Exception):
    pass


class _ContinueException(Exception):
    pass


class ZHTRuntimeError(Exception):
    pass


# ---------------------------------------------------------------------------
# Environment (scope stack)
# ---------------------------------------------------------------------------

class Environment:
    """A single frame in the environment stack."""
    def __init__(self, parent: Optional[Environment] = None):
        self.parent = parent
        self._store: Dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self._store[name] = value

    def get(self, name: str) -> Any:
        if name in self._store:
            return self._store[name]
        if self.parent:
            return self.parent.get(name)
        raise ZHTRuntimeError(f"Undefined variable '{name}'")

    def set(self, name: str, value: Any) -> None:
        if name in self._store:
            self._store[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        # Create in current frame (global assignment)
        self._store[name] = value


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interpreter:
    def __init__(self, program: Program, inputs: List[str] = None):
        self.program = program
        self.inputs: List[str] = list(inputs) if inputs else []
        self.output_lines: List[str] = []
        self._funcs: Dict[str, FuncDecl] = {}

    def run(self) -> str:
        # Register functions
        for decl in self.program.declarations:
            if isinstance(decl, FuncDecl):
                self._funcs[decl.name] = decl

        # Execute top-level variable declarations and any loose statements
        global_env = Environment()
        for decl in self.program.declarations:
            if isinstance(decl, VarDecl):
                self._exec(decl, global_env)

        # Run main() if it exists, otherwise run top-level statements
        if "main" in self._funcs:
            try:
                self._call_func("main", [], global_env)
            except _ReturnException:
                pass
        else:
            # Execute non-function, non-vardecl top-level items
            for decl in self.program.declarations:
                if not isinstance(decl, (FuncDecl, VarDecl)):
                    try:
                        self._exec(decl, global_env)
                    except _ReturnException:
                        break

        return "\n".join(self.output_lines)

    # ------------------------------------------------------------------
    # Statement execution
    # ------------------------------------------------------------------

    def _exec(self, stmt: Any, env: Environment) -> None:  # noqa: C901
        if isinstance(stmt, VarDecl):
            if stmt.size is not None:
                env.define(stmt.name, [0] * stmt.size)
            else:
                val = self._eval(stmt.init, env) if stmt.init is not None else self._default(stmt.typ)
                env.define(stmt.name, val)

        elif isinstance(stmt, Assign):
            val = self._eval(stmt.value, env)
            if isinstance(stmt.target, VarRef):
                env.set(stmt.target.name, val)
            elif isinstance(stmt.target, ArrayAccess):
                arr = env.get(stmt.target.name)
                idx = int(self._eval(stmt.target.index, env))
                arr[idx] = val

        elif isinstance(stmt, Show):
            val = self._eval(stmt.expr, env)
            self.output_lines.append(self._to_str(val))

        elif isinstance(stmt, Scan):
            raw = self.inputs.pop(0) if self.inputs else ""
            if isinstance(stmt.var, VarRef):
                # try to coerce based on current value type
                try:
                    existing = env.get(stmt.var.name)
                except ZHTRuntimeError:
                    existing = None
                env.set(stmt.var.name, self._coerce(raw, existing))
            elif isinstance(stmt.var, ArrayAccess):
                arr = env.get(stmt.var.name)
                idx = int(self._eval(stmt.var.index, env))
                existing = arr[idx] if arr else None
                arr[idx] = self._coerce(raw, existing)

        elif isinstance(stmt, When):
            cond = self._eval(stmt.cond, env)
            if self._truthy(cond):
                inner = Environment(parent=env)
                self._exec(stmt.then_block, inner)
            elif stmt.else_block:
                inner = Environment(parent=env)
                self._exec(stmt.else_block, inner)

        elif isinstance(stmt, Choose):
            switch_val = self._eval(stmt.expr, env)
            matched = False
            for case_val_node, case_blk in stmt.cases:
                case_val = self._eval(case_val_node, env)
                if switch_val == case_val:
                    self._exec(case_blk, Environment(parent=env))
                    matched = True
                    break
            if not matched and stmt.default:
                self._exec(stmt.default, Environment(parent=env))

        elif isinstance(stmt, While):
            while True:
                if not self._truthy(self._eval(stmt.cond, env)):
                    break
                try:
                    self._exec(stmt.body, Environment(parent=env))
                except _BreakException:
                    break
                except _ContinueException:
                    continue

        elif isinstance(stmt, RangeLoop):
            inner = Environment(parent=env)
            if stmt.init:
                self._exec(stmt.init, inner)
            while True:
                if stmt.cond and not self._truthy(self._eval(stmt.cond, inner)):
                    break
                try:
                    self._exec(stmt.body, Environment(parent=inner))
                except _BreakException:
                    break
                except _ContinueException:
                    pass
                if stmt.step:
                    if isinstance(stmt.step, Assign):
                        self._exec(stmt.step, inner)
                    else:
                        self._eval(stmt.step, inner)

        elif isinstance(stmt, Block):
            for s in stmt.statements:
                self._exec(s, env)

        elif isinstance(stmt, Give):
            val = self._eval(stmt.expr, env) if stmt.expr is not None else None
            raise _ReturnException(val)

        elif isinstance(stmt, Break):
            raise _BreakException()

        elif isinstance(stmt, Skip):
            raise _ContinueException()

        else:
            # expression-statement
            self._eval(stmt, env)

    # ------------------------------------------------------------------
    # Expression evaluation
    # ------------------------------------------------------------------

    def _eval(self, expr: Any, env: Environment) -> Any:  # noqa: C901
        if isinstance(expr, Literal):
            return expr.value

        if isinstance(expr, VarRef):
            return env.get(expr.name)

        if isinstance(expr, ArrayAccess):
            arr = env.get(expr.name)
            idx = int(self._eval(expr.index, env))
            return arr[idx]

        if isinstance(expr, Unary):
            operand = self._eval(expr.operand, env)
            if expr.op == "-":
                return -operand
            if expr.op == "!":
                return not self._truthy(operand)
            return operand

        if isinstance(expr, Binary):
            left = self._eval(expr.left, env)
            op = expr.op
            # Short-circuit for logical operators
            if op == "&&":
                return self._truthy(left) and self._truthy(self._eval(expr.right, env))
            if op == "||":
                return self._truthy(left) or self._truthy(self._eval(expr.right, env))
            right = self._eval(expr.right, env)
            if op == "+":
                # support string concatenation
                if isinstance(left, str) or isinstance(right, str):
                    return str(left) + str(right)
                return left + right
            if op == "-": return left - right
            if op == "*": return left * right
            if op == "/":
                if right == 0:
                    raise ZHTRuntimeError("Division by zero")
                return left / right if isinstance(left, float) or isinstance(right, float) else left // right
            if op == "%": return left % right
            if op == "==": return left == right
            if op == "!=": return left != right
            if op == "<":  return left < right
            if op == "<=": return left <= right
            if op == ">":  return left > right
            if op == ">=": return left >= right
            return None

        if isinstance(expr, FuncCall):
            args = [self._eval(a, env) for a in expr.args]
            return self._call_func(expr.name, args, env)

        return None

    # ------------------------------------------------------------------
    # Function call
    # ------------------------------------------------------------------

    def _call_func(self, name: str, args: List[Any], env: Environment) -> Any:
        func = self._funcs.get(name)
        if func is None:
            raise ZHTRuntimeError(f"Undefined function '{name}'")
        frame = Environment(parent=env)
        for param, val in zip(func.params, args):
            frame.define(param.name, val)
        try:
            self._exec(func.body, frame)
        except _ReturnException as ret:
            return ret.value
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truthy(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return val not in ("", "no", "false", "0")
        return bool(val)

    @staticmethod
    def _to_str(val: Any) -> str:
        if isinstance(val, bool):
            return "yes" if val else "no"
        if isinstance(val, float):
            # trim unnecessary trailing zeros
            formatted = f"{val:g}"
            return formatted
        return str(val)

    @staticmethod
    def _default(typ: str) -> Any:
        if typ == "whole":
            return 0
        if typ == "real":
            return 0.0
        if typ == "flag":
            return False
        if typ in ("text", "letter"):
            return ""
        return None

    @staticmethod
    def _coerce(raw: str, existing: Any) -> Any:
        """Coerce a raw string input to match the type of the existing value."""
        if isinstance(existing, bool):
            return raw.strip().lower() in ("yes", "true", "1")
        if isinstance(existing, int):
            try:
                return int(raw.strip())
            except ValueError:
                return 0
        if isinstance(existing, float):
            try:
                return float(raw.strip())
            except ValueError:
                return 0.0
        return raw
