#!/usr/bin/env python3
import argparse
from pathlib import Path

from patent_skill.validators import load_json, validate_claim_support

parser = argparse.ArgumentParser()
parser.add_argument("matrix", type=Path)
args = parser.parse_args()
errors = validate_claim_support(load_json(args.matrix))
for error in errors:
    print(f"FAIL {error}")
raise SystemExit(bool(errors))
