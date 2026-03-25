from planner import MockPlanner, PlannerError
from validator import PlanValidationError, PlanValidator


def test_planner_creates_typed_plan_for_supported_request(tmp_path) -> None:
    planner = MockPlanner()

    plan = planner.create_plan(
        "Add a --dry-run flag and update tests",
        target_repo=str(tmp_path),
    )

    assert [step.id for step in plan.steps] == [
        "inspect_repo",
        "propose_patch",
        "apply_patch",
        "run_tests",
        "run_lint",
        "summarize_results",
    ]
    assert plan.steps[3].retry_policy.retryable is True


def test_planner_rejects_unsupported_request(tmp_path) -> None:
    planner = MockPlanner()

    try:
        planner.create_plan("Deploy this service to prod", target_repo=str(tmp_path))
    except PlannerError as exc:
        assert "Unsupported request" in str(exc)
    else:
        raise AssertionError("Expected PlannerError for unsupported request")


def test_validator_requires_validation_steps(tmp_path) -> None:
    planner = MockPlanner()
    validator = PlanValidator()
    plan = planner.create_plan("Add a --dry-run flag and update tests", target_repo=str(tmp_path))
    invalid_plan = plan.__class__(
        run_id=plan.run_id,
        request=plan.request,
        target_repo=plan.target_repo,
        created_at=plan.created_at,
        steps=plan.steps[:-2],
    )

    try:
        validator.validate(invalid_plan)
    except PlanValidationError as exc:
        assert "run_lint" in str(exc) or "run_tests" in str(exc)
    else:
        raise AssertionError("Expected PlanValidationError for missing validation steps")
