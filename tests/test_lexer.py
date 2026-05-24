import unittest

from mini_compiler.lexer import Lexer
from mini_compiler.token import TokenType


class LexerTests(unittest.TestCase):
    def test_tokenizes_keywords_and_literals(self) -> None:
        tokens = Lexer("whole x = 1; flag ok = yes;").tokenize()
        kinds = [token.type for token in tokens]
        self.assertEqual(
            kinds[:8],
            [
                TokenType.TYPE,
                TokenType.IDENTIFIER,
                TokenType.ASSIGN,
                TokenType.INT_LITERAL,
                TokenType.SEMICOLON,
                TokenType.TYPE,
                TokenType.IDENTIFIER,
                TokenType.ASSIGN,
            ],
        )

    def test_skips_comments(self) -> None:
        tokens = Lexer("whole a; // comment\n/* block */ real b;").tokenize()
        lexemes = [token.lexeme for token in tokens if token.type != TokenType.EOF]
        self.assertEqual(lexemes, ["whole", "a", ";", "real", "b", ";"])


if __name__ == "__main__":
    unittest.main()
