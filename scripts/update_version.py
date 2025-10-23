#!/usr/bin/env python3
"""
Usage:
  python scripts/update_version.py 0.9.1 path/to/__init__.py

This updates the __version__ = 'x.y.z' (or using double quotes) assignment in the file.
"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 3:
    print("Usage: update_version.py <version> <path-to-init-py>")
    sys.exit(2)

new_version = sys.argv[1].strip()
file_path = Path(sys.argv[2])

if not file_path.exists():
    print(f"Error: file not found: {file_path}")
    sys.exit(1)

text = file_path.read_text(encoding="utf-8")

pattern = re.compile(r"^(__version__\s*=\s*)(['\"])([^'\"]*)(['\"])",
                     re.MULTILINE)

if not pattern.search(text):
    print(f"Error: __version__ assignment not found in {file_path}")
    sys.exit(1)

new_text = pattern.sub(rf"\1\2{new_version}\4", text, count=1)
file_path.write_text(new_text, encoding="utf-8")
print(f"Updated {file_path} -> __version__ = '{new_version}'")
