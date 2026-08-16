#!/usr/bin/env python3
import argparse
from pathlib import Path

from patent_skill.claims import validate_background_assertions
from patent_skill.validators import load_json

parser = argparse.ArgumentParser()
parser.add_argument("assertions", type=Path)
args = parser.parse_args()
errors = validate_background_assertions(load_json(args.assertions))
for error in errors:
    print(f"FAIL {error}")
raise SystemExit(bool(errors))
