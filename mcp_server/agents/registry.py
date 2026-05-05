"""Load per-agent surface từ surfaces.yaml + resolve handler."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Awaitable, Callable

import yaml

SURFACES_PATH = Path(__file__).with_name("surfaces.yaml")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[..., Awaitable[dict]]
    pii: bool


@dataclass(frozen=True)
class AgentSurface:
    agent_id: str
    description: str
    scopes_required: tuple[str, ...]
    rate_limit_rpm: int
    tools: dict[str, ToolSpec]


def _resolve(handler: str) -> Callable[..., Awaitable[dict]]:
    module_path, _, attr = handler.partition(":")
    module = importlib.import_module(module_path)
    return getattr(module, attr)


@lru_cache(maxsize=1)
def load_surfaces() -> dict[str, AgentSurface]:
    raw = yaml.safe_load(SURFACES_PATH.read_text(encoding="utf-8"))
    tool_specs: dict[str, ToolSpec] = {
        item["name"]: ToolSpec(name=item["name"], handler=_resolve(item["handler"]), pii=bool(item.get("pii", False)))
        for item in raw["tools"]
    }

    surfaces: dict[str, AgentSurface] = {}
    for agent_id, cfg in raw["agents"].items():
        tools_for_agent: dict[str, ToolSpec] = {}
        for tname in cfg["tools"]:
            if tname not in tool_specs:
                raise ValueError(f"agent {agent_id} references unknown tool {tname}")
            tools_for_agent[tname] = tool_specs[tname]
        if len(tools_for_agent) > 10:
            raise ValueError(f"agent {agent_id} exceeds 10-tool surface limit")
        surfaces[agent_id] = AgentSurface(
            agent_id=agent_id,
            description=cfg["description"],
            scopes_required=tuple(cfg.get("scopes_required", [])),
            rate_limit_rpm=int(cfg.get("rate_limit_rpm", 60)),
            tools=tools_for_agent,
        )
    return surfaces
