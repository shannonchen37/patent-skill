#!/usr/bin/env python3
import argparse
from pathlib import Path

from patent_skill.validators import validate_disclosure_file

parser = argparse.ArgumentParser()
parser.add_argument("draft", type=Path)
parser.add_argument("forbidden_values", type=Path)
args = parser.parse_args()
errors = validate_disclosure_file(args.draft, args.forbidden_values)
for error in errors:
    print(f"FAIL {error}")
raise SystemExit(bool(errors))
