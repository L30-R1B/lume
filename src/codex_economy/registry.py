"""Installed adapter entry points implement supports(path), extract(path, source), capabilities()."""

from importlib.metadata import entry_points
from typing import Protocol


class Adapter(Protocol):
    name: str
    version: str

    def supports(self, path: str) -> bool: ...
    def extract(self, path: str, source: str) -> dict: ...
    def capabilities(self) -> dict: ...


def installed():
    return {ep.name: ep.load()() for ep in entry_points(group="codex_economy.adapters")}


def validate(fact):
    if not isinstance(fact, dict) or not isinstance(fact.get("adapter"), str):
        raise ValueError("Adapter returned invalid metadata")
    for field in ("symbols", "relations", "warnings"):
        if not isinstance(fact.get(field), list):
            raise ValueError("Adapter missing " + field)
    for symbol in fact["symbols"]:
        if (
            len(symbol) != 5
            or not isinstance(symbol[0], str)
            or not 1 <= symbol[2] <= symbol[3]
            or symbol[4] not in ("resolved_by_tool", "observed", "inferred")
        ):
            raise ValueError("Invalid symbol contract")
    for relation in fact["relations"]:
        if (
            len(relation) != 3
            or not isinstance(relation[0], str)
            or relation[2] not in ("resolved_by_tool", "observed", "inferred")
        ):
            raise ValueError("Invalid relation contract")
    return fact
