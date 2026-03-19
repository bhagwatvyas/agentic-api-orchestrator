import json

from main import main


def test_main_plan_only_prints_json(capsys) -> None:
    main(["--plan-only", "What's the weather in Lisbon?"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload == [{"tool": "get_weather", "args": {"city": "Lisbon"}}]
