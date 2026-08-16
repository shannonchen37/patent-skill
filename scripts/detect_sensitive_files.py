#!/usr/bin/env python3
import argparse
from pathlib import Path

from patent_skill.security import detect_sensitive_files

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path)
args = parser.parse_args()
for path in detect_sensitive_files(args.project):
    print(f"SECURITY WARNING: {path}")
