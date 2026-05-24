from __future__ import annotations

from dataclasses import dataclass

from .ir import IRProgram


@dataclass(slots=True)
class RuntimeResult:
    output: list[str]
    return_value: object | None
    errors: list[str]


class IRExecutor:
    def __init__(self, program: IRProgram, inputs: list[object] | None = None) -> None:
        self.program = program
        self.inputs = list(inputs or [])
        self.output: list[str] = []
        self.errors: list[str] = []
        self.env: dict[str, object] = {}

    def run_main(self) -> RuntimeResult:
        instructions = self.program.instructions
        labels = {ins.arg1: idx for idx, ins in enumerate(instructions) if ins.op == "label" and ins.arg1 is not None}

        pc = 0
        running_main = False
        skipping_other_function = False
        return_value: object | None = None

        while pc < len(instructions):
            ins = instructions[pc]

            if ins.op == "function":
                if ins.arg1 == "main":
                    running_main = True
                    skipping_other_function = False
                else:
                    skipping_other_function = True
                pc += 1
                continue

            if ins.op == "end_function":
                if running_main:
                    break
                skipping_other_function = False
                pc += 1
                continue

            if skipping_other_function:
                pc += 1
                continue

            if running_main or ins.op in {"decl", "assign"}:
                jump = self._execute_instruction(ins, labels)
                if jump is not None:
                    pc = jump
                    continue
                if ins.op == "return":
                    return_value = self._resolve(ins.arg1) if ins.arg1 is not None else None
                    break

            pc += 1

        return RuntimeResult(output=self.output, return_value=return_value, errors=self.errors)

    def _execute_instruction(self, ins, labels: dict[str, int]) -> int | None:
        if ins.op == "decl":
            if ins.arg2 is not None:
                self.env.setdefault(ins.arg2, 0)
            return None

        if ins.op == "assign":
            if ins.result is not None:
                self.env[ins.result] = self._resolve(ins.arg1)
            return None

        if ins.op == "unary":
            operand = self._resolve(ins.arg2)
            value = None
            if ins.arg1 == "-":
                value = -float(operand) if isinstance(operand, float) else -int(operand)
            elif ins.arg1 == "!":
                value = not self._truthy(operand)
            if ins.result is not None:
                self.env[ins.result] = value
            return None

        if ins.op == "binary":
            left_name, right_name = (ins.arg2 or ",").split(",", 1)
            left = self._resolve(left_name.strip())
            right = self._resolve(right_name.strip())
            op = ins.arg1
            value = self._binary(op, left, right)
            if ins.result is not None:
                self.env[ins.result] = value
            return None

        if ins.op == "ifz":
            cond = self._resolve(ins.arg1)
            if not self._truthy(cond):
                return labels.get(ins.result or "")
            return None

        if ins.op == "goto":
            return labels.get(ins.arg1 or "")

        if ins.op == "label":
            return None

        if ins.op == "print":
            self.output.append(str(self._resolve(ins.arg1)))
            return None

        if ins.op == "read":
            if not self.inputs:
                self.errors.append(f"Runtime input exhausted for variable {ins.arg1}")
                self.env[ins.arg1 or "_"] = 0
                return None
            self.env[ins.arg1 or "_"] = self.inputs.pop(0)
            return None

        if ins.op in {"param", "call"}:
            self.errors.append("Runtime does not execute user-defined calls in this build.")
            if ins.result:
                self.env[ins.result] = 0
            return None

        return None

    def _resolve(self, name: object | None) -> object:
        if name is None:
            return 0
        token = str(name).strip()
        if token in self.env:
            return self.env[token]
        lower = token.lower()
        if lower in {"true", "yes"}:
            return True
        if lower in {"false", "no"}:
            return False
        if token.replace(".", "", 1).isdigit() and token.count(".") <= 1:
            if "." in token:
                return float(token)
            return int(token)
        return token

    def _truthy(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)

    def _binary(self, op: str | None, left: object, right: object) -> object:
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "%":
            return left % right
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == "&&":
            return self._truthy(left) and self._truthy(right)
        if op == "||":
            return self._truthy(left) or self._truthy(right)
        return 0
