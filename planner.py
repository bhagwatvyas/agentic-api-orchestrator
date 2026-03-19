from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from typing import Any


@dataclass(slots=True)
class PlanStep:
    """One executable unit in a workflow plan."""

    tool: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlannerError(Exception):
    """Raised when a user request cannot be transformed into a valid plan."""


class BasicPlanner:
    """
    Minimal planner stub.

    In production this class should call an LLM and validate the JSON output
    against the PlanStep schema. For now it uses lightweight heuristics so the
    rest of the system can be exercised end-to-end.
    """

    def create_plan(self, user_request: str) -> list[PlanStep]:
        normalized = user_request.strip()
        if not normalized:
            raise PlannerError("User request cannot be empty.")

        inferred = self._infer_travel_plan(normalized)
        if inferred:
            return inferred

        raise PlannerError(
            "Planner stub could not infer a workflow. "
            "Replace BasicPlanner with an LLM-backed planner for broader support."
        )

    def create_plan_json(self, user_request: str) -> str:
        return json.dumps([step.to_dict() for step in self.create_plan(user_request)], indent=2)

    def _infer_travel_plan(self, user_request: str) -> list[PlanStep]:
        lower = user_request.lower()

        route_match = re.search(
            r"from\s+(?P<origin>[a-zA-Z\s]+?)\s+to\s+(?P<destination>[a-zA-Z\s]+?)(?:\s+(?:and|with)\b|[?.!,]|$)",
            user_request,
            re.IGNORECASE,
        )
        city_match = re.search(r"\bin\s+(?P<city>[a-zA-Z\s]+)", user_request, re.IGNORECASE)

        steps: list[PlanStep] = []

        if "flight" in lower or "flights" in lower:
            if not route_match:
                raise PlannerError("Flight search requires an origin and destination in the request.")

            origin = route_match.group("origin").strip(" ,.?!")
            destination = route_match.group("destination").strip(" ,.?!")
            steps.append(
                PlanStep(
                    tool="search_flights",
                    args={"origin": origin, "destination": destination},
                )
            )

            if "hotel" in lower or "hotels" in lower:
                steps.append(
                    PlanStep(
                        tool="search_hotels",
                        args={"city": "{{state.steps.0.output.destination}}"},
                    )
                )

            if "weather" in lower:
                steps.append(
                    PlanStep(
                        tool="get_weather",
                        args={"city": "{{state.steps.0.output.destination}}"},
                    )
                )

            return steps

        if "hotel" in lower or "hotels" in lower:
            city = self._extract_city(city_match, user_request)
            steps.append(PlanStep(tool="search_hotels", args={"city": city}))
            if "weather" in lower:
                steps.append(PlanStep(tool="get_weather", args={"city": city}))
            return steps

        if "weather" in lower:
            city = self._extract_city(city_match, user_request)
            return [PlanStep(tool="get_weather", args={"city": city})]

        return []

    @staticmethod
    def _extract_city(city_match: re.Match[str] | None, user_request: str) -> str:
        if city_match:
            return city_match.group("city").strip(" ,.?!")
        raise PlannerError(f"Could not infer a city from request: {user_request!r}")
