# ZHT Compiler — Design & Implementation Report

**Course:** CSC303L — Compiler Construction  
**Department:** Computer Science, UET New Campus, Lahore  
**Submission Deadline:** 07-06-2026

---

## 1. Introduction

This project designs and implements a full mini-compiler for **ZHT**, a custom C-like programming language. The compiler processes source code through five integrated phases: lexical analysis, syntax analysis, semantic analysis, symbol table management, and intermediate code generation. A runtime interpreter executes the compiled AST, and an interactive web IDE (Streamlit) exposes all phases visually.

The ZHT language uses domain-specific keywords (`when`, `loop`, `scan`, `show`, etc.) to clearly distinguish it from C while retaining the same structural semantics, making it easy to evaluate compiler concepts in isolation from language familiarity.

---

## 2. ZHT Language Specification

### 2.1 Data Types

| ZHT Type | Equivalent | Description              |
|----------|------------|--------------------------|
| `whole`  | `int`      | Integer numbers          |
| `real`   | `float`    | Floating-point numbers   |
| `flag`   | `bool`     | Boolean (`yes` / `no`)   |
| `letter` | `char`     | Single character literal |
| `text`   | `string`   | String literal           |
| `empty`  | `void`     | Function return void     |

### 2.2 Keywords

| Category           | Keywords                                         |
|--------------------|--------------------------------------------------|
| Control flow       | `when`, `otherwise`, `choose`, `case`, `default` |
| Loops              | `loop`, `range`, `break`, `skip`                 |
| Functions          | `give` (return)                                  |
| I/O                | `scan` (input), `show` (output)                  |
| Boolean literals   | `yes`, `no`                                      |

### 2.3 Operators

- **Arithmetic:** `+`, `-`, `*`, `/`, `%`
- **Relational:** `<`, `>`, `<=`, `>=`
- **Equality:** `==`, `!=`
- **Logical:** `&&`, `||`, `!`
- **Assignment:** `=`

---

## 3. System Architecture

The compiler is structured as a pipeline of independent, testable modules:

```
Source Code
    │
    ▼
┌─────────┐   tokens   ┌──────────┐   AST    ┌──────────────┐
│  Lexer  │ ─────────► │  Parser  │ ────────► │  Semantics   │
└─────────┘            └──────────┘           └──────────────┘
                            │                        │
                     parse errors             semantic errors
                                                     │
                                                     ▼
                                             ┌──────────────┐
                                             │ IR Generator │
                                             └──────────────┘
                                                     │
                                                   TAC IR
                                                     │
                                                     ▼
                                             ┌──────────────┐
                                             │  Interpreter │
                                             └──────────────┘
                                                     │
                                               Program Output
```

| Module               | File                          | Responsibility                                |
|----------------------|-------------------------------|-----------------------------------------------|
| Lexer                | `zht_compiler/lexer.py`       | Tokenise source text                          |
| Parser               | `zht_compiler/parser.py`      | Build AST, panic-mode error recovery          |
| Semantic Analyzer    | `zht_compiler/semantics.py`   | Type checking, scope resolution, declarations |
| Symbol Table         | `zht_compiler/semantics.py`   | Scoped `Symbol`/`Scope` classes               |
| IR Generator         | `zht_compiler/ir.py`          | Emit Three-Address Code                       |
| Runtime Interpreter  | `zht_compiler/runtime.py`     | AST-walking interpreter                       |
| Compiler Engine      | `zht_compiler/compiler_engine.py` | Orchestrates all phases                   |
| Web IDE              | `app.py`                      | Streamlit UI with phase inspection tabs       |

---

## 4. Formal Grammar (BNF)

```
program         → declaration*

declaration     → type IDENTIFIER array_decl? ( func_decl | var_decl )
array_decl      → "[" INT_LITERAL "]"
func_decl       → "(" param_list? ")" block
var_decl        → ( "=" expression )? ";"
param_list      → type IDENTIFIER ( "," type IDENTIFIER )*

block           → "{" declaration* "}"

statement       → when_stmt
                | choose_stmt
                | loop_stmt
                | range_stmt
                | "break" ";"
                | "skip" ";"
                | "give" expression? ";"
                | "scan" "(" var_target ")" ";"
                | "show" "(" expression ")" ";"
                | block
                | expression ( "=" expression )? ";"

when_stmt       → "when" "(" expression ")" block
                  ( "otherwise" block )?

choose_stmt     → "choose" "(" expression ")" "{"
                  ( "case" expression ":" statement* )*
                  ( "default" ":" statement* )?
                  "}"

loop_stmt       → "loop" "(" expression ")" block

range_stmt      → "range" "(" declaration? ";" expression? ";" step? ")" block
step            → expression ( "=" expression )?

expression      → or_expr
or_expr         → and_expr ( "||" and_expr )*
and_expr        → equality ( "&&" equality )*
equality        → comparison ( ( "==" | "!=" ) comparison )*
comparison      → term ( ( "<" | ">" | "<=" | ">=" ) term )*
term            → factor ( ( "+" | "-" ) factor )*
factor          → unary ( ( "*" | "/" | "%" ) unary )*
unary           → ( "!" | "-" ) unary | primary
primary         → INT_LITERAL | FLOAT_LITERAL | STRING_LITERAL | CHAR_LITERAL
                | "yes" | "no"
                | IDENTIFIER ( "(" arg_list? ")" | "[" expression "]" )?
                | "(" expression ")"

var_target      → IDENTIFIER ( "[" expression "]" )?
arg_list        → expression ( "," expression )*

type            → "whole" | "real" | "flag" | "letter" | "text" | "empty"
```

---

## 5. Phase 1 — Lexical Analysis

### 5.1 Design

The lexer is a stateful, character-by-character scanner implemented in `lexer.py`. It produces a flat list of `Token(type, lexeme, line, column, literal)` frozen dataclass objects. An explicit `TokenType` enum (defined in `token.py`) prevents string-comparison bugs.

### 5.2 Token Categories

| Category           | Examples                                    |
|--------------------|---------------------------------------------|
| Type keywords      | `whole`, `real`, `flag`, `letter`, `text`, `empty` |
| Statement keywords | `when`, `otherwise`, `loop`, `range`, `scan`, `show`, `give`, `break`, `skip` |
| Identifiers        | `myVar`, `result`, `count`                  |
| Integer literals   | `0`, `42`, `-7`                             |
| Float literals     | `3.14`, `0.5`                               |
| String literals    | `"hello world"`                             |
| Char literals      | `'a'`, `'\n'`                               |
| Boolean literals   | `yes`, `no`                                 |
| Operators          | `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `&&`, `||`, `!` |
| Delimiters         | `(`, `)`, `{`, `}`, `[`, `]`, `,`, `;`, `:` |
| EOF sentinel       | `EOF`                                       |

### 5.3 Error Handling

Unrecognised characters raise `LexerError` with line and column information. The compiler engine catches this and reports it before attempting to parse.

---

## 6. Phase 2 — Syntax Analysis

### 6.1 Design

The parser is a hand-written **recursive-descent parser** that maps directly to the BNF grammar. Each non-terminal has a corresponding `_method()`. Operator precedence is encoded via the expression hierarchy: `_or()` → `_and()` → `_equality()` → `_comparison()` → `_term()` → `_factor()` → `_unary()` → `_primary()`.

### 6.2 Panic-Mode Error Recovery

The parser implements **panic-mode error recovery** via the `_synchronize()` method. When a `ParseError` is raised inside `parse()`, the parser:

1. Records the error message in `self.errors`.
2. Calls `_synchronize()`, which discards tokens until it reaches a safe boundary:
   - A **semicolon** `";"` — end of a broken statement (consumed).
   - A **closing brace** `"}"` — end of a block (not consumed; caller handles it).
   - A **type keyword** — start of a new declaration.
   - A **statement keyword** — start of a new statement.
3. Parsing resumes at the next safe token.

This ensures **all syntax errors are collected in one pass**, not just the first, which is far more useful for the programmer. This technique is analogous to the synchronize function in Crafting Interpreters (Nystrom, 2021) and to the `yyerror`/error token mechanism in Yacc/Bison.

### 6.3 AST Node Types

All AST nodes are frozen dataclasses defined in `ast.py`:

`Program`, `FuncDecl`, `VarDecl`, `Block`, `When`, `Choose`, `While`, `RangeLoop`, `Assign`, `Give`, `Break`, `Skip`, `Scan`, `Show`, `Binary`, `Unary`, `FuncCall`, `ArrayAccess`, `VarRef`, `Literal`

---

## 7. Phase 3 — Semantic Analysis & Symbol Table

### 7.1 Symbol Table Design

The symbol table uses a **linked-scope chain**: each `Scope` object holds a dictionary of `name → Symbol` and a pointer to its `parent` scope. This naturally models lexical scoping.

```
Global Scope
│  factorial : func(whole) -> whole
│  n         : whole
│
└── Function Scope (factorial)
    │  x     : whole
    │  result : whole
    └── Block Scope (if)
        │  temp  : whole
```

Each `Symbol` stores:
- `name` — identifier string
- `typ` — ZHT type name (`whole`, `real`, etc.)
- `size` — array length (or `None` for scalars)
- `is_func` — flag for function symbols
- `param_types` — list of parameter types
- `ret_type` — return type for functions

Lookup traverses from the current scope upward to global, implementing lexical scoping. Redeclaration in the same scope raises an error.

### 7.2 Semantic Checks Performed

| Check                          | Example Error                                      |
|--------------------------------|----------------------------------------------------|
| Undeclared variable use        | `Undeclared identifier 'x' at line 5`              |
| Redeclaration in same scope    | `'count' already declared in this scope`           |
| Type mismatch in assignment    | `Cannot assign real to whole variable 'n'`         |
| Binary operand type mismatch   | `Operator '+' not applicable to flag and whole`    |
| Wrong argument count           | `'add' expects 2 arguments, got 3`                 |
| Wrong argument type            | `Argument 1 of 'add': expected whole, got real`    |
| Return type mismatch           | `Function 'f' returns whole, got real`             |
| Non-boolean condition          | `Condition of 'when' must be flag, got whole`      |
| Array index not integer        | `Array index must be whole, got real`              |
| Break/skip outside loop        | `'break' used outside of a loop`                   |

### 7.3 Error Collection Strategy

The semantic analyzer never raises exceptions; it appends all errors to `self.errors` and continues. This is an **error-accumulation** strategy (as opposed to fail-fast), allowing the programmer to see all issues in one compilation pass.

---

## 8. Phase 4 — Intermediate Code Generation

### 8.1 IR Format

The IR generator produces **Three-Address Code (TAC)** — a linear list of instructions where each instruction has at most one operator and three operands. TAC is a widely used IR form because it is easy to generate from a tree, easy to optimise, and straightforward to translate to machine code.

### 8.2 Instruction Set

| Instruction                     | Meaning                          |
|---------------------------------|----------------------------------|
| `function <name>`               | Function entry point             |
| `param_decl <name> <type>`      | Declare function parameter       |
| `endfunc <name>`                | Function end marker              |
| `alloc <name> <type>`           | Allocate scalar variable         |
| `alloc_array <name> <size>`     | Allocate array variable          |
| `assign <dest> <src>`           | Simple copy                      |
| `<op> <dest> <left> <right>`    | Binary arithmetic/relational     |
| `neg <dest> <src>`              | Unary minus                      |
| `not <dest> <src>`              | Logical NOT                      |
| `label <L>`                     | Branch target                    |
| `if_false <cond> goto <L>`      | Conditional branch (false)       |
| `goto <L>`                      | Unconditional branch             |
| `param <arg>`                   | Push call argument               |
| `call <dest> <func> <nargs>`    | Call function                    |
| `return <val>` / `return`       | Return value or void             |
| `print <val>`                   | Output to stdout                 |
| `scan <var>`                    | Read from stdin into variable    |
| `store <arr> <idx> <val>`       | Array element write              |
| `load <tmp> <arr> <idx>`        | Array element read               |

### 8.3 Example

ZHT source:
```
whole factorial(whole n) {
    when (n <= 1) { give 1; }
    give n * factorial(n - 1);
}
```

Generated TAC (abbreviated):
```
function factorial
param_decl n whole
    alloc _t0 whole
    <= _t0 n 1
    if_false _t0 goto L0
    return 1
label L0
    alloc _t1 whole
    - _t2 n 1
    param _t2
    call _t3 factorial 1
    * _t1 n _t3
    return _t1
endfunc factorial
```

---

## 9. Phase 5 — Runtime Interpreter

The interpreter is an **AST-walking interpreter** implemented in `runtime.py`. It traverses the AST directly rather than executing TAC, making the control flow straightforward to implement. Special Python exceptions (`_ReturnException`, `_BreakException`, `_ContinueException`) handle non-local exits from functions and loops cleanly without polluting the traversal logic.

An `Environment` class forms a linked chain of scopes mirroring the semantic `Scope` chain, so variable lookup during execution uses the same lexical scoping rules enforced at compile time.

---

## 10. Error Handling Summary

| Phase     | Technique                       | Recovery Strategy                        |
|-----------|---------------------------------|------------------------------------------|
| Lexer     | Immediate exception             | Fail-fast; report first illegal char     |
| Parser    | Panic-mode synchronization      | Skip to `;` / `}` / keyword boundary; collect all errors |
| Semantics | Error accumulation              | Never raises; appends to error list; continues analysis |
| Runtime   | Python exception wrapping       | Catches all runtime exceptions; reports as string |

---

## 11. Test Cases

### 11.1 Valid Programs (from Streamlit IDE sample loader)

| Program              | Features Tested                               |
|----------------------|-----------------------------------------------|
| Bubble Sort          | Arrays, nested `range` loops, swapping        |
| Fibonacci            | Recursion, `range` loop, `give`               |
| FizzBuzz             | `loop`, `flag` type, `when/otherwise`         |
| Grade Calculator     | `scan`, `when/otherwise` chaining, `real`     |
| Semantic Error Demo  | Undeclared variable, type mismatch detection  |

### 11.2 Error Detection Tests

**Invalid syntax** — missing semicolon triggers `ParseError`:
```zht
whole x = 5    ← missing ;
whole y = 10;
```
Expected: parse error at line 1 AND line 2 continues to parse (error recovery).

**Undeclared identifier**:
```zht
whole main() {
    show(result);   ← result never declared
}
```
Expected: `Undeclared identifier 'result' at line 2`.

**Type mismatch**:
```zht
whole main() {
    whole x = 3.14;   ← real literal assigned to whole
}
```
Expected: `Cannot assign real to whole variable 'x'`.

---

## 12. Design Choices and Comparisons

### 12.1 Hand-written Parser vs. Parser Generator

| Aspect               | Hand-written (this project)       | Parser Generator (Yacc/ANTLR)         |
|----------------------|-----------------------------------|---------------------------------------|
| Grammar readability  | Grammar implicit in code          | Explicit grammar file (`.g4`, `.y`)   |
| Error messages       | Fully customisable                | Generic by default                    |
| Error recovery       | Custom `_synchronize()`           | Built-in `error` token / default recovery |
| Maintainability      | Harder for large grammars         | Easy to extend grammar                |
| Educational value    | High — see every detail           | Lower — generator abstracts details   |

For a compiler construction lab, a hand-written parser provides far deeper insight into the parsing process.

### 12.2 AST Interpreter vs. TAC Execution

This project generates TAC IR (for display and analysis) but executes using the **AST-walking interpreter** for correctness and simplicity. Executing TAC would require a separate virtual machine with its own memory model, which adds complexity without adding new compiler concepts for this scope.

### 12.3 Error Accumulation vs. Fail-Fast

The semantic analyzer uses error accumulation (similar to Java's `javac` and Rust's `rustc`) rather than fail-fast (like many early C compilers). This is strictly better for usability: the programmer sees all errors in one pass.

### 12.4 Scoped Symbol Table vs. Flat Table

A flat symbol table cannot represent shadowing or block-scoped variables. The linked-scope chain directly models the ZHT source language's block structure and is the standard approach in production compilers (e.g., GCC's scope stack, Clang's `DeclContext` chain).

---

## 13. Conclusion

This project fully implements all five required compiler phases for the ZHT language:

1. **Lexical analysis** — complete tokenizer with line/column tracking.
2. **Syntax analysis** — recursive-descent parser with panic-mode error recovery that collects all syntax errors.
3. **Semantic analysis** — full type checking, scope resolution, declaration validation, and function signature checking, with error accumulation.
4. **Symbol table** — linked-scope chain supporting nested scopes, arrays, and function metadata.
5. **Intermediate code generation** — Three-Address Code with full instruction coverage for all language constructs.

Additionally, an AST-walking interpreter executes programs interactively and a Streamlit web IDE exposes all compiler phases for inspection. The design is modular, extensible, and directly mirrors the architecture taught in compiler construction courses.

