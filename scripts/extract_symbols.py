#!/usr/bin/env python3
import argparse
from pathlib import Path

from patent_skill.symbols import write_symbols

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
write_symbols(args.project, args.output)
