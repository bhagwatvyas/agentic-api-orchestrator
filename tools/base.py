from __future__ import annotations

from dataclasses import dataclass
from inspect import signature
from typing import Any, Callable


class ToolError(Exception):
    """Raised for invalid tool registration or invocation."""


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    func: Callable[..., Any]

    @property
    def schema(self) -> dict[str, Any]:
        params = []
        for parameter in signature(self.func).parameters.values():
            params.append(
                {
                    "name": parameter.name,
                    "required": parameter.default is parameter.empty,
                    "annotation": str(parameter.annotation),
                }
            )
        return {
            "name": self.name,
            "description": self.description,
            "parameters": params,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ToolError(f"Tool {tool.name!r} is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._tools))
            raise ToolError(f"Unknown tool {name!r}. Available tools: {available}") from exc

    def invoke(self, name: str, **kwargs: Any) -> Any:
        tool = self.get(name)
        return tool.func(**kwargs)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema for tool in self._tools.values()]
