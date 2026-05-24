from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Symbol:
    name: str
    kind: str
    type_name: str
    scope_level: int
    params: list[str] = field(default_factory=list)
    line: int = 0
    column: int = 0


class SymbolTable:
    def __init__(self) -> None:
        self.scopes: list[dict[str, Symbol]] = [{}]

    @property
    def level(self) -> int:
        return len(self.scopes) - 1

    def push(self) -> None:
        self.scopes.append({})

    def pop(self) -> None:
        if len(self.scopes) == 1:
            raise RuntimeError("Cannot pop global scope")
        self.scopes.pop()

    def define(self, symbol: Symbol) -> bool:
        scope = self.scopes[-1]
        if symbol.name in scope:
            return False
        scope[symbol.name] = symbol
        return True

    def resolve(self, name: str) -> Symbol | None:
        for scope in reversed(self.scopes):
            symbol = scope.get(name)
            if symbol is not None:
                return symbol
        return None

    def resolve_current(self, name: str) -> Symbol | None:
        return self.scopes[-1].get(name)
