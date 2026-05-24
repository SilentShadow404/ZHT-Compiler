import unittest

from mini_compiler.symbols import Symbol, SymbolTable


class SymbolTableTests(unittest.TestCase):
    def test_nested_scope_lookup(self) -> None:
        table = SymbolTable()
        self.assertTrue(table.define(Symbol("x", "var", "int", 0)))
        table.push()
        self.assertIsNotNone(table.resolve("x"))
        self.assertTrue(table.define(Symbol("y", "var", "float", 1)))
        table.pop()
        self.assertIsNone(table.resolve("y"))


if __name__ == "__main__":
    unittest.main()
