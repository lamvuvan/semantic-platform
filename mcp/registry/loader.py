"""Load tool registry từ YAML và resolve handler bằng entry point."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

REGISTRY_PATH = Path(__file__).with_name("tools.yaml")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    description: str
    scopes: tuple[str, ...]
    pii: bool
    handler: Callable[..., Any]
    input_schema: dict[str, Any]


def _resolve_handler(path: str) -> Callable[..., Any]:
    module_path, _, attr = path.partition(":")
    if not module_path or not attr:
        raise ValueError(f"invalid handler reference: {path}")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


def load_registry(path: Path | None = None) -> list[ToolSpec]:
    raw = yaml.safe_load((path or REGISTRY_PATH).read_text())
    tools: list[ToolSpec] = []
    for item in raw["tools"]:
        tools.append(
            ToolSpec(
                name=item["name"],
                version=item["version"],
                description=item["description"],
                scopes=tuple(item.get("scopes", [])),
                pii=bool(item.get("pii", False)),
                handler=_resolve_handler(item["handler"]),
                input_schema=item["input_schema"],
            )
        )
    return tools
