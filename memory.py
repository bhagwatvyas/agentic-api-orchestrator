from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class WorkflowState:
    """
    Stores intermediate data so later steps can reference previous outputs.

    Data is kept in a simple nested dictionary to make serialization and debug
    inspection straightforward.
    """

    data: dict[str, Any] = field(
        default_factory=lambda: {
            "steps": [],
            "tool_outputs": {},
            "context": {},
        }
    )

    def set_context(self, key: str, value: Any) -> None:
        self.data["context"][key] = value

    def add_step_result(self, *, tool_name: str, args: dict[str, Any], output: Any) -> None:
        step_index = len(self.data["steps"])
        record = {
            "index": step_index,
            "tool": tool_name,
            "args": args,
            "output": output,
        }
        self.data["steps"].append(record)
        self.data["tool_outputs"].setdefault(tool_name, []).append(output)

    def snapshot(self) -> dict[str, Any]:
        return self.data

    def get(self, path: str) -> Any:
        """
        Resolves dotted paths like:
        - steps.0.output.city
        - tool_outputs.search_flights.0.options
        - context.original_request
        """

        current: Any = self.data
        for part in path.split("."):
            if isinstance(current, list):
                current = current[int(part)]
                continue

            if isinstance(current, dict):
                if part not in current:
                    raise KeyError(f"State path not found: {path}")
                current = current[part]
                continue

            raise KeyError(f"Cannot traverse path {path!r} beyond {part!r}")

        return current
