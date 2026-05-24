from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import compile_source
from .zht_spec import LANGUAGE_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description=f"{LANGUAGE_NAME} compiler (C-like custom language)")
    parser.add_argument("source", help="Path to source file")
    parser.add_argument("--tokens", action="store_true", help="Print tokens and stop")
    parser.add_argument("--run", action="store_true", help="Execute program after successful compilation")
    parser.add_argument(
        "--inputs",
        default="",
        help="Comma-separated runtime values consumed by scan(...), e.g. '5, 2.5, yes'",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    source = source_path.read_text(encoding="utf-8")

    runtime_inputs: list[object] = []
    if args.inputs.strip():
        for raw in [item.strip() for item in args.inputs.split(",") if item.strip()]:
            low = raw.lower()
            if low in {"yes", "true"}:
                runtime_inputs.append(True)
            elif low in {"no", "false"}:
                runtime_inputs.append(False)
            elif raw.replace(".", "", 1).isdigit() and raw.count(".") <= 1:
                runtime_inputs.append(float(raw) if "." in raw else int(raw))
            else:
                runtime_inputs.append(raw)

    result = compile_source(source, runtime_inputs=runtime_inputs, run=args.run)
    if args.tokens:
        print("\n".join(f"{token.type.name:<14} {token.lexeme}" for token in result.tokens))
        return 0

    if result.parse_errors:
        print("Parse errors:")
        for error in result.parse_errors:
            print(f"- {error}")
        return 1

    if result.semantic_errors:
        print("Semantic errors:")
        for error in result.semantic_errors:
            print(f"- {error}")
        return 1

    if result.ir is not None:
        print(result.ir.render())
    else:
        print("Compilation completed with no intermediate code")

    if args.run and result.runtime is not None:
        print("\nRuntime output:")
        if result.runtime.output:
            for line in result.runtime.output:
                print(f"- {line}")
        else:
            print("- <no output>")
        if result.runtime.errors:
            print("Runtime diagnostics:")
            for error in result.runtime.errors:
                print(f"- {error}")
    return 0
