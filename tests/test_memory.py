from memory import WorkflowState


def test_workflow_state_stores_and_resolves_nested_values() -> None:
    state = WorkflowState()
    state.set_context("original_request", "Plan a trip")
    state.add_step_result(
        tool_name="search_flights",
        args={"origin": "SFO", "destination": "Tokyo"},
        output={"destination": "Tokyo", "options": [{"airline": "SkyJet"}]},
    )

    assert state.get("context.original_request") == "Plan a trip"
    assert state.get("steps.0.output.destination") == "Tokyo"
    assert state.get("tool_outputs.search_flights.0.options.0.airline") == "SkyJet"
