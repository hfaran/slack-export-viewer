#!/usr/bin/env python3
"""
Generate a simple changelog from git commits.

Usage:
  python scripts/generate_changelog.py --output changelog.md
  python scripts/generate_changelog.py --since v0.9.0 --output changelog.md

The script writes a markdown-formatted changelog listing commits grouped by
subject lines and includes author and short hash.
"""
import argparse
import subprocess
from pathlib import Path
import sys
import shlex

def run_cmd(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{proc.stderr}")
    return proc.stdout.strip()

def generate_changelog(since_tag=None):
    if since_tag:
        range_spec = f"{since_tag}..HEAD"
    else:
        # full history
        range_spec = "HEAD"
    # Use pretty format: - subject (short-hash) — Author
    # Use --no-merges to avoid merge commits if you prefer.
    git_cmd = f"git log {shlex.quote(range_spec)} --pretty=format:'- %s (%h) — %an' --no-decorate --no-merges"
    try:
        out = run_cmd(git_cmd)
    except RuntimeError as e:
        # If git log fails (e.g., invalid tag), fallback to full history
        print("git log failed, falling back to full history:", file=sys.stderr)
        out = run_cmd("git log HEAD --pretty=format:'- %s (%h) — %an' --no-decorate --no-merges")
    if not out.strip():
        out = "*No commits found for this range.*"
    header = "# Changelog\n\n"
    return header + out + "\n"

def main():
    parser = argparse.ArgumentParser(description="Generate a changelog from git commits.")
    parser.add_argument("--since", help="Tag or commit to start from (exclusive). If omitted, uses full history.")
    parser.add_argument("--output", default="changelog.md", help="Output markdown file.")
    args = parser.parse_args()

    try:
        changelog = generate_changelog(args.since)
    except Exception as e:
        print(f"Error generating changelog: {e}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.output)
    out_path.write_text(changelog, encoding="utf-8")
    print(f"Wrote changelog to {out_path}")

if __name__ == "__main__":
    main()
