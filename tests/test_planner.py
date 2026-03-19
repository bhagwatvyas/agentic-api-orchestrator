from planner import BasicPlanner, PlannerError


def test_planner_creates_chained_travel_plan() -> None:
    planner = BasicPlanner()

    plan = planner.create_plan("Find flights from San Francisco to Tokyo and hotels there and weather there")

    assert [step.tool for step in plan] == [
        "search_flights",
        "search_hotels",
        "get_weather",
    ]
    assert plan[0].args == {"origin": "San Francisco", "destination": "Tokyo"}
    assert plan[1].args == {"city": "{{state.steps.0.output.destination}}"}
    assert plan[2].args == {"city": "{{state.steps.0.output.destination}}"}


def test_planner_raises_on_empty_request() -> None:
    planner = BasicPlanner()

    try:
        planner.create_plan("   ")
    except PlannerError as exc:
        assert "cannot be empty" in str(exc)
    else:
        raise AssertionError("Expected PlannerError for empty input")


def test_planner_requires_city_for_weather_only_request() -> None:
    planner = BasicPlanner()

    try:
        planner.create_plan("Tell me the weather")
    except PlannerError as exc:
        assert "Could not infer a city" in str(exc)
    else:
        raise AssertionError("Expected PlannerError when city is missing")
