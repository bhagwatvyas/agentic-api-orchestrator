from __future__ import annotations

from tools.base import Tool, ToolRegistry
from tools.travel import get_weather, search_flights, search_hotels


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="search_flights",
            description="Search available flights between two locations.",
            func=search_flights,
        )
    )
    registry.register(
        Tool(
            name="search_hotels",
            description="Search hotels in a city.",
            func=search_hotels,
        )
    )
    registry.register(
        Tool(
            name="get_weather",
            description="Retrieve weather information for a city.",
            func=get_weather,
        )
    )
    return registry


__all__ = ["Tool", "ToolRegistry", "build_default_registry"]
