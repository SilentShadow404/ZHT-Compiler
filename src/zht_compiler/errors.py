class CompilerError(Exception):
    """Base class for ZHT compiler errors."""


class LexerError(CompilerError):
    """Raised when the scanner cannot tokenize the source text."""

