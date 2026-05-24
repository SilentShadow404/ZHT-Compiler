from __future__ import annotations

from dataclasses import dataclass

from .ir import IRGenerator, IRProgram
from .lexer import Lexer
from .parser import Parser
from .runtime import IRExecutor, RuntimeResult
from .semantics import SemanticAnalyzer
from .token import Token


@dataclass(slots=True)
class CompilationResult:
    tokens: list[Token]
    parse_errors: list[str]
    semantic_errors: list[str]
    ir: IRProgram | None
    runtime: RuntimeResult | None


def compile_source(source: str, runtime_inputs: list[object] | None = None, run: bool = False) -> CompilationResult:
    tokens = Lexer(source).tokenize()
    parser = Parser(tokens)
    program = parser.parse()
    if parser.errors:
        return CompilationResult(tokens, parser.errors, [], None, None)

    semantic = SemanticAnalyzer()
    semantic_result = semantic.analyze(program)
    if semantic_result.errors:
        return CompilationResult(tokens, [], semantic_result.errors, None, None)

    ir = IRGenerator().generate(program)
    runtime_result = None
    if run:
        runtime_result = IRExecutor(ir, runtime_inputs).run_main()
    return CompilationResult(tokens, [], [], ir, runtime_result)
