import json
from pathlib import Path


def test_all_json_files_parse() -> None:
    root = Path(__file__).parents[1]
    files = list((root / "schemas").glob("*.json"))
    assert files
    for path in files:
        json.loads(path.read_text(encoding="utf-8"))
