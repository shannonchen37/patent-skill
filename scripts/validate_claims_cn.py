#!/usr/bin/env python3
import argparse
from pathlib import Path

from patent_skill.claims import validate_claims_cn

parser = argparse.ArgumentParser()
parser.add_argument("claims", type=Path)
args = parser.parse_args()
errors = validate_claims_cn(args.claims.read_text(encoding="utf-8"))
for error in errors:
    print(f"FAIL {error}")
raise SystemExit(bool(errors))
