class CompilerError(Exception):
    """Base compiler error."""


class LexerError(CompilerError):
    """Raised when the scanner cannot tokenize the input."""


class ParseError(CompilerError):
    """Raised when the parser encounters unrecoverable syntax issues."""


class SemanticError(CompilerError):
    """Raised when semantic analysis fails."""
