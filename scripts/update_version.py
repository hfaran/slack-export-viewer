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

match = pattern.search(text)
if not match:
    print(f"Error: __version__ assignment not found in {file_path}")
    sys.exit(1)

# Use a callable replacement to avoid ambiguous backreference parsing
new_text = pattern.sub(
    lambda m: f"{m.group(1)}{m.group(2)}{new_version}{m.group(4)}",
    text,
    count=1,
)
file_path.write_text(new_text, encoding="utf-8")

quote = match.group(2)
print(f"Updated {file_path} -> __version__ = {quote}{new_version}{quote}")
