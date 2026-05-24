from .errors import LexerError
from .lexer import Lexer
from .parser import Parser, ParseError
from .semantics import SemanticAnalyzer
from .ir import IRGenerator
from .runtime import Interpreter
from .token import Token
from typing import List


class CompilationResult:
    def __init__(self, tokens: List[Token], ast, sem_errors: List[str], ir):
        self.tokens = tokens
        self.ast = ast
        self.sem_errors = sem_errors
        self.ir = ir


class CompilerEngine:
    def __init__(self):
        pass

    def compile(self, source: str) -> CompilationResult:
        # --- Lexing ---
        lexer = Lexer(source)
        try:
            tokens = lexer.tokenize()
        except LexerError as exc:
            return CompilationResult([], None, [str(exc)], None)

        # --- Parsing ---
        parser = Parser(tokens)
        try:
            ast = parser.parse()
        except ParseError as e:
            return CompilationResult(tokens, None, [str(e)], None)

        # --- Semantic analysis (collect ALL errors, never raise) ---
        sem = SemanticAnalyzer()
        sem.analyze(ast)

        # --- IR generation (always generate, even if there are semantic warnings) ---
        ir = None
        if not sem.errors:
            irgen = IRGenerator()
            ir = irgen.generate(ast)

        return CompilationResult(tokens, ast, sem.errors, ir)

    def run(self, comp: CompilationResult, inputs: List[str]) -> str:
        """Execute using the AST-walking interpreter.  IR is for display only."""
        if comp.ast is None:
            return "Cannot run: compilation failed."
        interp = Interpreter(comp.ast, inputs)
        try:
            return interp.run()
        except Exception as exc:
            return f"Runtime error: {exc}"

