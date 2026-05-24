import unittest

from mini_compiler.compiler import compile_source


class CompilerTests(unittest.TestCase):
    def test_valid_program_compiles_to_ir(self) -> None:
        with open("examples/valid_minimal.mc", encoding="utf-8") as handle:
            result = compile_source(handle.read(), run=True)
        self.assertEqual(result.parse_errors, [])
        self.assertEqual(result.semantic_errors, [])
        self.assertIsNotNone(result.ir)
        self.assertIn("function | main", result.ir.render())
        self.assertIsNotNone(result.runtime)
        self.assertEqual(result.runtime.output, ["10"])

    def test_semantic_error_for_undeclared_identifier(self) -> None:
        with open("examples/invalid_undeclared.mc", encoding="utf-8") as handle:
            result = compile_source(handle.read())
        self.assertEqual(result.parse_errors, [])
        self.assertTrue(result.semantic_errors)
        self.assertIn("undeclared", result.semantic_errors[0].lower())

    def test_parse_error_for_missing_semicolon(self) -> None:
        with open("examples/invalid_syntax.mc", encoding="utf-8") as handle:
            result = compile_source(handle.read())
        self.assertTrue(result.parse_errors)


if __name__ == "__main__":
    unittest.main()
