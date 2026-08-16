from pathlib import Path

from patent_skill.symbols import extract_symbols


def test_extracts_python_symbols(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('class Node:\n    """A node."""\n    def score(self):\n        return 1\n')
    symbols = extract_symbols(tmp_path)
    assert {item["symbol"] for item in symbols} == {"Node", "score"}
    assert next(item for item in symbols if item["symbol"] == "Node")["docstring"] == "A node."


def test_fallback_extracts_go_function(tmp_path: Path) -> None:
    (tmp_path / "a.go").write_text("func SelectNode() {}\n")
    assert extract_symbols(tmp_path)[0]["symbol"] == "SelectNode"
