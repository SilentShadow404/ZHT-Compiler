"""
Intermediate Representation Generator for ZHT.

Produces Three-Address Code (TAC) from the AST.
TAC instruction formats:
  alloc <name> <type>
  alloc_array <name> <size>
  assign <target> <value>
  store <array> <index> <value>     -- array[index] = value
  load <temp> <array> <index>       -- temp = array[index]
  <op> <dest> <left> <right>        -- arithmetic / relational binary
  neg <dest> <src>                  -- unary minus
  not <dest> <src>                  -- logical NOT
  label <L>
  if_false <cond> goto <L>
  goto <L>
  param <arg>
  call <dest> <func> <nargs>
  return <val>
  return
  print <val>
  scan <var>
  scani <array> <index>
  function <name>
  param_decl <name> <type>
  endfunc <name>
"""
from typing import List, Any, Optional
from .ast import (
    ArrayAccess, Assign, Binary, Block, Break, Choose, FuncCall,
    FuncDecl, Give, Literal, Program, RangeLoop, Scan, Show,
    Skip, Unary, VarDecl, VarRef, When, While,
)


class IRProgram:
    def __init__(self):
        self.instructions: List[str] = []

    def emit(self, code: str) -> None:
        self.instructions.append(code)

    def __repr__(self) -> str:
        return "\n".join(self.instructions)


class IRGenerator:
    def __init__(self):
        self.temp_counter = 0
        self.label_counter = 0
        # stack of (continue_label, break_label) for nested loops
        self._loop_stack: List[tuple] = []

    def new_temp(self) -> str:
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def new_label(self) -> str:
        lbl = f"L{self.label_counter}"
        self.label_counter += 1
        return lbl

    # ------------------------------------------------------------------
    # Top-level
    # ------------------------------------------------------------------

    def generate(self, program: Program) -> IRProgram:
        ir = IRProgram()
        for d in program.declarations:
            if isinstance(d, VarDecl):
                self._gen_var_decl(d, ir)
            elif isinstance(d, FuncDecl):
                self._gen_func(d, ir)
        return ir

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def _gen_var_decl(self, d: VarDecl, ir: IRProgram) -> None:
        if d.size is not None:
            ir.emit(f"alloc_array {d.name} {d.size}")
        else:
            ir.emit(f"alloc {d.name} {d.typ}")
        if d.init is not None:
            val = self._expr(d.init, ir)
            ir.emit(f"assign {d.name} {val}")

    def _gen_func(self, func: FuncDecl, ir: IRProgram) -> None:
        ir.emit(f"function {func.name}")
        for p in func.params:
            ir.emit(f"param_decl {p.name} {p.typ}")
        self._gen_block(func.body, ir)
        ir.emit(f"endfunc {func.name}")

    # ------------------------------------------------------------------
    # Block
    # ------------------------------------------------------------------

    def _gen_block(self, block: Block, ir: IRProgram) -> None:
        for stmt in block.statements:
            self._gen_stmt(stmt, ir)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _gen_stmt(self, stmt: Any, ir: IRProgram) -> None:  # noqa: C901
        if isinstance(stmt, VarDecl):
            self._gen_var_decl(stmt, ir)

        elif isinstance(stmt, Assign):
            val = self._expr(stmt.value, ir)
            if isinstance(stmt.target, VarRef):
                ir.emit(f"assign {stmt.target.name} {val}")
            elif isinstance(stmt.target, ArrayAccess):
                idx = self._expr(stmt.target.index, ir)
                ir.emit(f"store {stmt.target.name} {idx} {val}")

        elif isinstance(stmt, Show):
            val = self._expr(stmt.expr, ir)
            ir.emit(f"print {val}")

        elif isinstance(stmt, Scan):
            if isinstance(stmt.var, VarRef):
                ir.emit(f"scan {stmt.var.name}")
            elif isinstance(stmt.var, ArrayAccess):
                idx = self._expr(stmt.var.index, ir)
                ir.emit(f"scani {stmt.var.name} {idx}")

        elif isinstance(stmt, When):
            cond = self._expr(stmt.cond, ir)
            else_label = self.new_label()
            end_label = self.new_label()
            ir.emit(f"if_false {cond} goto {else_label}")
            self._gen_block(stmt.then_block, ir)
            if stmt.else_block:
                ir.emit(f"goto {end_label}")
            ir.emit(f"label {else_label}")
            if stmt.else_block:
                self._gen_block(stmt.else_block, ir)
                ir.emit(f"label {end_label}")

        elif isinstance(stmt, Choose):
            # Compile as a chain of if_eq checks
            end_label = self.new_label()
            expr_t = self._expr(stmt.expr, ir)
            next_labels = [self.new_label() for _ in stmt.cases]
            for i, (val, blk) in enumerate(stmt.cases):
                val_t = self._expr(val, ir)
                cmp_t = self.new_temp()
                ir.emit(f"== {cmp_t} {expr_t} {val_t}")
                ir.emit(f"if_false {cmp_t} goto {next_labels[i]}")
                self._gen_block(blk, ir)
                ir.emit(f"goto {end_label}")
                ir.emit(f"label {next_labels[i]}")
            if stmt.default:
                self._gen_block(stmt.default, ir)
            ir.emit(f"label {end_label}")

        elif isinstance(stmt, While):
            cond_label = self.new_label()
            end_label = self.new_label()
            ir.emit(f"label {cond_label}")
            cond = self._expr(stmt.cond, ir)
            ir.emit(f"if_false {cond} goto {end_label}")
            self._loop_stack.append((cond_label, end_label))
            self._gen_block(stmt.body, ir)
            self._loop_stack.pop()
            ir.emit(f"goto {cond_label}")
            ir.emit(f"label {end_label}")

        elif isinstance(stmt, RangeLoop):
            # init
            if stmt.init:
                self._gen_stmt(stmt.init, ir)
            cond_label = self.new_label()
            end_label = self.new_label()
            step_label = self.new_label()
            ir.emit(f"label {cond_label}")
            if stmt.cond:
                cond = self._expr(stmt.cond, ir)
                ir.emit(f"if_false {cond} goto {end_label}")
            self._loop_stack.append((step_label, end_label))
            self._gen_block(stmt.body, ir)
            self._loop_stack.pop()
            ir.emit(f"label {step_label}")
            if stmt.step:
                if isinstance(stmt.step, Assign):
                    self._gen_stmt(stmt.step, ir)
                else:
                    self._expr(stmt.step, ir)
            ir.emit(f"goto {cond_label}")
            ir.emit(f"label {end_label}")

        elif isinstance(stmt, Break):
            if self._loop_stack:
                _, end_label = self._loop_stack[-1]
                ir.emit(f"goto {end_label}")

        elif isinstance(stmt, Skip):
            if self._loop_stack:
                cont_label, _ = self._loop_stack[-1]
                ir.emit(f"goto {cont_label}")

        elif isinstance(stmt, Give):
            if stmt.expr is None:
                ir.emit("return")
            else:
                val = self._expr(stmt.expr, ir)
                ir.emit(f"return {val}")

        elif isinstance(stmt, Block):
            self._gen_block(stmt, ir)

        else:
            # expression-statement
            self._expr(stmt, ir)

    # ------------------------------------------------------------------
    # Expressions  →  returns a TAC operand string
    # ------------------------------------------------------------------

    def _expr(self, expr: Any, ir: IRProgram) -> str:  # noqa: C901
        if isinstance(expr, Literal):
            if isinstance(expr.value, str):
                return f'"{expr.value}"'
            if isinstance(expr.value, bool):
                return "1" if expr.value else "0"
            return repr(expr.value)

        if isinstance(expr, VarRef):
            return expr.name

        if isinstance(expr, ArrayAccess):
            idx = self._expr(expr.index, ir)
            t = self.new_temp()
            ir.emit(f"load {t} {expr.name} {idx}")
            return t

        if isinstance(expr, Binary):
            left = self._expr(expr.left, ir)
            right = self._expr(expr.right, ir)
            t = self.new_temp()
            ir.emit(f"{expr.op} {t} {left} {right}")
            return t

        if isinstance(expr, Unary):
            operand = self._expr(expr.operand, ir)
            t = self.new_temp()
            op_name = "neg" if expr.op == "-" else "not"
            ir.emit(f"{op_name} {t} {operand}")
            return t

        if isinstance(expr, FuncCall):
            args = [self._expr(a, ir) for a in expr.args]
            for a in args:
                ir.emit(f"param {a}")
            t = self.new_temp()
            ir.emit(f"call {t} {expr.name} {len(args)}")
            return t

        return "0"

