#!/usr/bin/env python3
import argparse
from pathlib import Path

from patent_skill.claims import validate_abstract_cn

parser = argparse.ArgumentParser()
parser.add_argument("abstract", type=Path)
args = parser.parse_args()
errors = validate_abstract_cn(args.abstract.read_text(encoding="utf-8"))
for error in errors:
    print(f"FAIL {error}")
raise SystemExit(bool(errors))
