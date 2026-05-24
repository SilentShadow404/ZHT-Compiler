# ZHT Compiler Playground

This project now defines and implements a new language called `ZHT` (C-like subset) and runs as a teaching compiler playground. It explains the language first, then lets you write code, compile through all phases, and run correct programs.

## What it supports

- lexical analysis
- syntax analysis with error recovery
- semantic analysis with scoped symbol tables
- intermediate code generation
- runtime execution of compiled IR
- token view, parse diagnostics, semantic diagnostics, and IR output

## ZHT language features

- basic types: `whole`, `real`, `flag`, `empty`
- boolean literals: `yes`, `no`
- variable declarations and assignments
- arithmetic, relational, equality, and logical expressions
- `when`, `otherwise`, `loop`, `range`
- function definitions, parameters, calls, and `give`
- `scan(identifier);` and `show(expression);`
- nested scopes and symbol resolution

## Run the playground

```bash
streamlit run app.py
```

## Run the compiler from the terminal

```bash
python -m mini_compiler examples/valid_minimal.mc
```

Run and execute after compilation:

```bash
python -m mini_compiler examples/valid_minimal.mc --run
python -m mini_compiler examples/valid_minimal.mc --run --inputs "5, yes"
```

Show tokens instead of compiling:

```bash
python -m mini_compiler examples/valid_minimal.mc --tokens
```

## Project structure

- `app.py` provides the interactive playground UI.
- `lexer.py` tokenizes source code.
- `parser.py` builds the AST.
- `semantics.py` validates declarations, types, and scope.
- `symbols.py` stores scoped identifiers.
- `ir.py` generates three-address code.
- `cli.py` keeps the terminal compiler entry point.

## Example input

```c
whole main() {
    whole a = 10;
    real b = 2.5;
    flag ok = yes;

    when (ok) {
        show(a);
    } otherwise {
        show(b);
    }

    give 0;
}
```

## Notes for the lab report

A strong report should explain:

- the grammar used by the parser
- token categories and lexical rules
- semantic checks and scope rules
- symbol table design
- intermediate code format
- recovery strategy for syntax errors
- valid and invalid test cases
