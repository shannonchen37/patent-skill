#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from patent_skill.validators import build_engineering_provenance, load_json

parser = argparse.ArgumentParser()
parser.add_argument("features", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
result = build_engineering_provenance(load_json(args.features))
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
