# Mini Compiler Report

## 1. Introduction

This project implements a mini compiler for a restricted C-like language subset. The goal is to demonstrate how lexical analysis, syntax analysis, semantic analysis, symbol table management, and intermediate code generation work together in a single pipeline.

## 2. Language Scope

Supported constructs:

- data types: `int`, `float`, `bool`
- variable declarations and assignments
- arithmetic, relational, equality, and logical expressions
- `if`, `if-else`, `while`, `for`
- functions with parameters and `return`
- `input(identifier);` and `output(expression);`

## 3. Architecture

The compiler is divided into modules:

- `lexer`: converts source text into tokens
- `parser`: builds an AST using recursive descent
- `semantics`: checks declarations, types, scopes, and function usage
- `symbols`: stores scoped symbol information
- `ir`: generates three-address style intermediate code
- `cli`: connects all phases for command-line use

## 4. Grammar Summary

A simplified grammar shape:

- program → declaration*
- declaration → type identifier (`(` parameters `)` block | `;` | `=` expression `;`)
- statement → block | declaration | assignment | if | while | for | return | input | output | expression `;`
- expression uses precedence for logical, equality, relational, additive, multiplicative, unary, and primary forms

## 5. Lexical Analysis

The scanner recognizes:

- keywords: `if`, `else`, `while`, `for`, `return`, `input`, `output`
- type names: `int`, `float`, `bool`, `void`
- identifiers, numeric literals, boolean literals
- operators, delimiters, and comments

## 6. Syntax Analysis

The parser is recursive descent with error recovery. It uses synchronization after syntax errors so later statements can still be analyzed.

## 7. Semantic Analysis

Semantic checks include:

- undeclared identifier detection
- redeclaration checks
- scope resolution
- assignment compatibility
- function call argument checking
- return type validation
- boolean condition validation for control flow

## 8. Symbol Table Design

The symbol table uses a stack of scopes. Each scope stores identifier name, category, type, nesting level, and parameter metadata for functions.

## 9. Intermediate Code

The compiler emits a three-address style IR using instructions such as:

- `function`, `end_function`
- `assign`, `binary`, `unary`
- `ifz`, `goto`, `label`
- `param`, `call`, `return`
- `read`, `print`

## 10. Error Handling

The compiler reports lexical, syntax, and semantic errors with line and column information. Syntax recovery allows parsing to continue after an error boundary.

## 11. Test Cases

Valid and invalid test cases are included in `examples/`:

- `valid_minimal.mc`
- `invalid_type.mc`
- `invalid_undeclared.mc`
- `invalid_syntax.mc`

## 12. Comparison and Analysis

Compared with a basic toy compiler, this project adds:

- scoped symbol management
- type-aware semantic validation
- structured IR generation
- recovery-oriented parsing
- reusable modular design

## 13. Conclusion

This implementation demonstrates the main phases of a compiler in an integrated, extensible structure suitable for a compiler construction lab submission.
