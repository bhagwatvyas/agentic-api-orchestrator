from executor import ExecutionError, WorkflowExecutor
from memory import WorkflowState
from planner import PlanStep
from tools import build_default_registry
from tools.base import Tool, ToolRegistry


def test_executor_resolves_state_placeholders_between_steps() -> None:
    executor = WorkflowExecutor(build_default_registry(), max_retries=1)
    state = WorkflowState()

    plan = [
        PlanStep(tool="search_flights", args={"origin": "San Francisco", "destination": "Tokyo"}),
        PlanStep(tool="search_hotels", args={"city": "{{state.steps.0.output.destination}}"}),
    ]

    results, final_state = executor.execute(plan, state=state)

    assert len(results) == 2
    assert results[1].output["city"] == "Tokyo"
    assert final_state.get("steps.1.args.city") == "Tokyo"


def test_executor_retries_before_succeeding() -> None:
    calls = {"count": 0}

    def flaky_tool(city: str) -> dict[str, str]:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary failure")
        return {"city": city}

    registry = ToolRegistry()
    registry.register(Tool(name="flaky_tool", description="Fails once", func=flaky_tool))
    executor = WorkflowExecutor(registry, max_retries=1)

    results, _ = executor.execute([PlanStep(tool="flaky_tool", args={"city": "Lisbon"})])

    assert calls["count"] == 2
    assert results[0].attempts == 2
    assert results[0].output == {"city": "Lisbon"}


def test_executor_raises_after_exhausting_retries() -> None:
    def broken_tool() -> None:
        raise RuntimeError("permanent failure")

    registry = ToolRegistry()
    registry.register(Tool(name="broken_tool", description="Always fails", func=broken_tool))
    executor = WorkflowExecutor(registry, max_retries=1)

    try:
        executor.execute([PlanStep(tool="broken_tool", args={})])
    except ExecutionError as exc:
        assert "broken_tool" in str(exc)
    else:
        raise AssertionError("Expected ExecutionError when retries are exhausted")
