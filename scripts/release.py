#!/usr/bin/env python3
"""Decide and prepare slack-export-viewer releases.

The next version is the highest of three levels, each computed by fixed rules:

* code: what changed in the shipped package since the last release tag. The
  click CLI is loaded at both refs and compared option by option (see
  diff_param), and the pyproject.toml metadata is compared too.
* commit titles: Conventional Commit types in commit subjects since the last
  tag (feat -> minor, fix/perf -> patch, "!" or a BREAKING CHANGE footer -> major).
* requested: an optional --bump floor.

Usage:
  python scripts/release.py plan [--head REF] [--bump auto|patch|minor|major] [--json]
  python scripts/release.py changelog --version X.Y.Z --notes FILE
"""
from __future__ import annotations

import argparse
import datetime
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = "slackviewer"
CHANGELOG_MARKER = "<!-- new releases are inserted below this line by scripts/release.py -->"

NONE, PATCH, MINOR, MAJOR = range(4)
LEVEL_NAMES = ["none", "patch", "minor", "major"]

RELEASE_TAG = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
RELEASE_COMMIT = re.compile(r"^Release \d+\.\d+\.\d+\b")
CONVENTIONAL = re.compile(r"^(?P<type>[A-Za-z]+)(?:\([^)]*\))?(?P<bang>!)?: \S")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:", re.MULTILINE)
# Keep in sync with the `types` list in .github/workflows/pr-title.yml.
TYPE_LEVELS = {"feat": MINOR, "fix": PATCH, "perf": PATCH}
OTHER_TYPES = {"build", "chore", "ci", "docs", "refactor", "revert", "style", "test"}


COMPUTED = "<computed>"


class SurfaceError(Exception):
    """The CLI could not be loaded at one of the refs being compared."""


# --- git ---------------------------------------------------------------------

def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    ).stdout


def file_at(ref: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


# --- versions ----------------------------------------------------------------

def parse_version(text: str) -> tuple[int, int, int] | None:
    match = RELEASE_TAG.match(text)
    return tuple(int(part) for part in match.groups()) if match else None


def format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def bump(version: tuple[int, int, int], level: int) -> tuple[int, int, int]:
    major, minor, patch = version
    if level == MAJOR:
        return (major + 1, 0, 0)
    if level == MINOR:
        return (major, minor + 1, 0)
    if level == PATCH:
        return (major, minor, patch + 1)
    return version


def latest_release_tag(head: str) -> str:
    tags = [tag for tag in git("tag", "--merged", head).split() if RELEASE_TAG.match(tag)]
    if not tags:
        raise SystemExit(f"No release tags (like 1.2.3) are reachable from {head}")
    return max(tags, key=parse_version)


# --- commit titles -----------------------------------------------------------

def classify_commit(subject: str, body: str = "") -> tuple[int, str | None]:
    """Return (level, type). type is None when the subject has no known Conventional Commit type."""
    match = CONVENTIONAL.match(subject)
    kind = match["type"].lower() if match else None
    if kind not in TYPE_LEVELS and kind not in OTHER_TYPES:
        kind = None
    if BREAKING_FOOTER.search(body) or (kind and match["bang"]):
        return MAJOR, kind
    return TYPE_LEVELS.get(kind, NONE), kind


def commits_between(base: str, head: str) -> list[dict]:
    log = git("log", "--no-merges", "--format=%H%x1f%s%x1f%b%x1e", f"{base}..{head}")
    commits = []
    for record in log.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, subject, body = record.split("\x1f", 2)
        if RELEASE_COMMIT.match(subject):
            continue
        level, kind = classify_commit(subject, body)
        commits.append({"sha": sha, "subject": subject, "type": kind, "level": level})
    return commits


# --- package metadata --------------------------------------------------------

def package_metadata(pyproject_text: str | None) -> dict:
    data = tomllib.loads(pyproject_text) if pyproject_text else {}
    poetry = data.get("tool", {}).get("poetry", {})
    project = data.get("project", {})

    deps = {
        name.lower(): spec if isinstance(spec, str) else json.dumps(spec, sort_keys=True)
        for name, spec in poetry.get("dependencies", {}).items()
    }
    python = deps.pop("python", None) or project.get("requires-python")
    for requirement in project.get("dependencies", []):
        deps[re.match(r"[A-Za-z0-9._-]+", requirement).group(0).lower()] = requirement

    scripts = {}
    for name, target in {**poetry.get("scripts", {}), **project.get("scripts", {})}.items():
        scripts[name] = target if isinstance(target, str) else target.get("reference", "")
    return {
        "version": poetry.get("version") or project.get("version"),
        "python": python,
        "dependencies": deps,
        "scripts": scripts,
    }


def console_scripts(ref: str, metadata: dict) -> dict[str, str]:
    """Entry points from pyproject.toml, falling back to setup.py for releases before Poetry."""
    if metadata["scripts"]:
        return metadata["scripts"]
    setup = file_at(ref, "setup.py") or ""
    return dict(re.findall(r"['\"]([\w-]+)\s*=\s*([\w.]+:[\w.]+)['\"]", setup))


def python_floor(spec: str | None) -> tuple[int, ...] | None:
    floors = []
    for clause in re.split(r"[,|]", spec or ""):
        match = re.match(r"\s*(>=|>|\^|~=|~|==)?\s*(\d+(?:\.\d+)*)", clause)
        if match:
            parts = [int(part) for part in match.group(2).split(".")]
            floors.append(tuple(parts + [0] * (3 - len(parts))))
    return min(floors) if floors else None


def diff_metadata(old: dict, new: dict) -> list[tuple[int, str]]:
    changes = []
    old_floor, new_floor = python_floor(old["python"]), python_floor(new["python"])
    # No floor means every Python was allowed, so adding one is a raise.
    if new_floor and new_floor != old_floor:
        raised = old_floor is None or new_floor > old_floor
        changes.append((
            MAJOR if raised else MINOR,
            f"minimum Python {'raised' if raised else 'lowered'}: `{old['python'] or 'unset'}` -> `{new['python']}`",
        ))
    old_deps, new_deps = old["dependencies"], new["dependencies"]
    for name in sorted(old_deps.keys() | new_deps.keys()):
        if name not in new_deps:
            changes.append((PATCH, f"dependency `{name}` removed"))
        elif name not in old_deps:
            changes.append((PATCH, f"dependency `{name}` added (`{new_deps[name]}`)"))
        elif old_deps[name] != new_deps[name]:
            changes.append((PATCH, f"dependency `{name}`: `{old_deps[name]}` -> `{new_deps[name]}`"))
    return changes


# --- CLI surface -------------------------------------------------------------

def describe_param(param) -> dict:
    import click

    envvar = param.envvar
    envvars = [envvar] if isinstance(envvar, str) else list(envvar or [])
    default = param.default
    return {
        "kind": "argument" if isinstance(param, click.Argument) else "option",
        "name": param.name,
        "opts": sorted({*param.opts, *param.secondary_opts}),
        "type": type(param.type).__name__,
        "choices": sorted(map(str, param.type.choices)) if isinstance(param.type, click.Choice) else None,
        "required": bool(param.required),
        "multiple": bool(param.multiple),
        "nargs": param.nargs,
        "is_flag": bool(getattr(param, "is_flag", False)),
        "envvars": sorted(envvars),
        "default": COMPUTED if callable(default) else repr(default),
    }


def dump_surface(src: str, scripts: dict[str, str]) -> dict[str, list[dict]]:
    """Describe every click command reachable from the console scripts.

    Imports the package from `src`, so it runs in a subprocess (see surface_of_tree)
    to keep two versions of the package from meeting in one interpreter.
    """
    sys.path.insert(0, src)
    import importlib

    import click

    surface: dict[str, list[dict]] = {}

    def walk(command, path):
        surface[path] = [describe_param(p) for p in command.params if not getattr(p, "hidden", False)]
        if isinstance(command, click.Group):
            for name, sub in sorted(command.commands.items()):
                if not sub.hidden:
                    walk(sub, f"{path} {name}")

    for script, target in sorted(scripts.items()):
        module, _, attr = target.partition(":")
        obj = importlib.import_module(module)
        for part in attr.split("."):
            obj = getattr(obj, part)
        if isinstance(obj, click.Command):
            walk(obj, script)
    return surface


def surface_of_tree(src: Path | str, scripts: dict[str, str]) -> dict[str, list[dict]]:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "surface.json"
        result = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve()), "surface", str(src), str(output)],
            input=json.dumps(scripts), capture_output=True, text=True,
        )
        if result.returncode != 0:
            lines = result.stderr.strip().splitlines()
            raise SurfaceError(lines[-1] if lines else f"exit code {result.returncode}")
        return json.loads(output.read_text())


def surface_at(ref: str, scripts: dict[str, str]) -> dict[str, list[dict]]:
    archive = subprocess.run(
        ["git", "archive", ref, PACKAGE_DIR], cwd=REPO_ROOT, check=True, capture_output=True
    ).stdout
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(tmp, filter="data")
        try:
            return surface_of_tree(tmp, scripts)
        except SurfaceError as error:
            raise SurfaceError(f"at {ref}: {error}") from None


def _label(param: dict) -> str:
    if param["kind"] == "argument":
        return param["name"].upper()
    return max(param["opts"], key=len)


def _same_param(a: dict, b: dict) -> bool:
    if a["kind"] != b["kind"]:
        return False
    if a["kind"] == "argument":
        return a["name"] == b["name"]
    return bool(set(a["opts"]) & set(b["opts"]))


def diff_param(label: str, old: dict, new: dict) -> list[tuple[int, str]]:
    changes = []

    def note(level, text):
        changes.append((level, f"{label}: {text}"))

    if lost := sorted(set(old["opts"]) - set(new["opts"])):
        note(MAJOR, f"no longer accepts {', '.join(lost)}")
    if gained := sorted(set(new["opts"]) - set(old["opts"])):
        note(MINOR, f"now also accepts {', '.join(gained)}")
    for key in ("type", "multiple", "nargs", "is_flag"):
        if old[key] != new[key]:
            note(MAJOR, f"{key} changed: {old[key]} -> {new[key]}")
    if new["required"] and not old["required"]:
        note(MAJOR, "is now required")
    if old["required"] and not new["required"]:
        note(MINOR, "is no longer required")
    old_choices, new_choices = set(old["choices"] or []), set(new["choices"] or [])
    if lost := sorted(old_choices - new_choices):
        note(MAJOR, f"choices removed: {', '.join(lost)}")
    if gained := sorted(new_choices - old_choices):
        note(MINOR, f"choices added: {', '.join(gained)}")
    if lost := sorted(set(old["envvars"]) - set(new["envvars"])):
        note(MAJOR, f"no longer reads {', '.join(lost)}")
    # A computed default is opaque: it may already have read the env var that
    # replaces it (1.9.1 moved SEV_ARCHIVE from a default callable to envvar=).
    opaque = COMPUTED in (old["default"], new["default"])
    if (gained := sorted(set(new["envvars"]) - set(old["envvars"]))) and not opaque:
        note(MINOR, f"now also reads {', '.join(gained)}")
    if old["default"] != new["default"] and not opaque:
        note(MINOR, f"default changed: {old['default']} -> {new['default']}")
    return changes


def diff_params(command: str, old_params: list[dict], new_params: list[dict]) -> list[tuple[int, str]]:
    changes = []
    unmatched = list(range(len(new_params)))
    for old in old_params:
        index = next((i for i in unmatched if _same_param(old, new_params[i])), None)
        label = f"`{command} {_label(old)}`"
        if index is None:
            changes.append((MAJOR, f"{label} removed"))
            continue
        unmatched.remove(index)
        changes += diff_param(label, old, new_params[index])
    for index in unmatched:
        new = new_params[index]
        label = f"`{command} {_label(new)}`"
        if new["required"]:
            changes.append((MAJOR, f"{label} added as a required {new['kind']}"))
        else:
            changes.append((MINOR, f"{label} added"))
    return changes


def diff_surface(old: dict, new: dict) -> list[tuple[int, str]]:
    changes = [(MAJOR, f"command `{command}` removed") for command in old if command not in new]
    for command in new:
        if command not in old:
            changes.append((MINOR, f"command `{command}` added"))
        else:
            changes += diff_params(command, old[command], new[command])
    return changes


# --- plan --------------------------------------------------------------------

def build_plan(head: str = "HEAD", requested: int = NONE, base: str | None = None) -> dict:
    head_sha = git("rev-parse", "--verify", f"{head}^{{commit}}").strip()
    base = base or latest_release_tag(head_sha)
    warnings = []

    commits = commits_between(base, head_sha)

    old_meta = package_metadata(file_at(base, "pyproject.toml"))
    new_meta = package_metadata(file_at(head_sha, "pyproject.toml"))
    shipped = [
        path for path in git("diff", "--name-only", base, head_sha).splitlines()
        if path.startswith(PACKAGE_DIR + "/")
    ]
    code_changes = []
    if shipped:
        code_changes.append((PATCH, f"{len(shipped)} file(s) changed under `{PACKAGE_DIR}/`"))
    code_changes += diff_metadata(old_meta, new_meta)

    surface_error = None
    old_scripts, new_scripts = console_scripts(base, old_meta), console_scripts(head_sha, new_meta)
    if shipped or old_scripts != new_scripts:
        try:
            code_changes += diff_surface(surface_at(base, old_scripts), surface_at(head_sha, new_scripts))
        except SurfaceError as error:
            surface_error = str(error)

    if new_meta["version"] and new_meta["version"] != base:
        warnings.append(
            f"pyproject.toml says {new_meta['version']} but the last release tag is {base}; "
            "the release sets it to the computed version."
        )

    code_level = max((level for level, _ in code_changes), default=NONE)
    commit_level = max((commit["level"] for commit in commits), default=NONE)
    level = max(code_level, commit_level, requested)
    return {
        "base": base,
        "head": head_sha,
        "release": level > NONE,
        "level": LEVEL_NAMES[level],
        "version": format_version(bump(parse_version(base), level)) if level > NONE else None,
        "signals": {
            "code": LEVEL_NAMES[code_level],
            "commits": LEVEL_NAMES[commit_level],
            "requested": LEVEL_NAMES[requested],
        },
        "code_changes": [
            {"level": LEVEL_NAMES[level], "detail": detail}
            for level, detail in sorted(code_changes, key=lambda change: -change[0])
        ],
        "commits": [{**commit, "level": LEVEL_NAMES[commit["level"]]} for commit in commits],
        "unclassified": [commit["sha"] for commit in commits if commit["type"] is None],
        "surface_error": surface_error,
        "warnings": warnings,
    }


def render_markdown(plan: dict) -> str:
    if plan["release"]:
        title = f"## Release plan: {plan['base']} → {plan['version']} ({plan['level']})"
    else:
        title = f"## Release plan: nothing to release since {plan['base']}"
    signals = plan["signals"]
    lines = [
        title,
        "",
        f"Compared tag `{plan['base']}` with `{plan['head'][:7]}` ({len(plan['commits'])} commit(s)).",
        "",
        "| Signal | Level |",
        "|---|---|",
        f"| Code (package files, CLI, metadata) | {signals['code']} |",
        f"| Commit titles | {signals['commits']} |",
        f"| Requested (`--bump`) | {signals['requested']} |",
    ]
    if plan["surface_error"]:
        lines += ["", f"**CLI check failed** ({plan['surface_error']}). Pass an explicit bump to release anyway."]
    if plan["code_changes"]:
        lines += ["", "### Code changes", ""]
        lines += [f"- **{change['level']}**: {change['detail']}" for change in plan["code_changes"]]
    if plan["commits"]:
        lines += ["", "### Commits", ""]
        for commit in plan["commits"]:
            kind = f"{commit['type']} ({commit['level']})" if commit["type"] else "no conventional type"
            lines.append(f"- `{commit['sha'][:7]}` {commit['subject']} — {kind}")
    if plan["unclassified"]:
        lines += [
            "",
            f"{len(plan['unclassified'])} commit(s) have no Conventional Commit type, "
            "so only the code check counted them.",
        ]
    if plan["warnings"]:
        lines += ["", "### Warnings", ""] + [f"- {warning}" for warning in plan["warnings"]]
    return "\n".join(lines) + "\n"


# --- changelog ---------------------------------------------------------------

def write_changelog(path: Path, version: str, notes: str, date: str) -> None:
    notes = re.sub(r"^(#{1,5}) ", r"#\1 ", notes.strip(), flags=re.MULTILINE)
    section = f"## {version} ({date})\n\n{notes}\n"
    text = path.read_text() if path.exists() else ""
    if CHANGELOG_MARKER not in text:
        raise SystemExit(f"{path} is missing the marker line: {CHANGELOG_MARKER}")
    before, _, after = text.partition(CHANGELOG_MARKER)
    after = after.lstrip("\n")
    path.write_text(f"{before}{CHANGELOG_MARKER}\n\n{section}" + (f"\n{after}" if after else ""))


# --- command line ------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    plan_cmd = commands.add_parser("plan", help="compute the next version")
    plan_cmd.add_argument("--head", default="HEAD", help="ref to release (default: HEAD)")
    plan_cmd.add_argument("--base", help="release tag to compare against (default: latest reachable)")
    plan_cmd.add_argument("--bump", choices=["auto", "patch", "minor", "major"], default="auto",
                          help="minimum level; the computed level wins if it is higher")
    plan_cmd.add_argument("--expect-version", default="", help="fail unless the computed version equals this")
    plan_cmd.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    plan_cmd.add_argument("--summary", help="also append the markdown plan to this file")
    plan_cmd.add_argument("--github-output", help="append release/version/previous/level to this file")

    changelog_cmd = commands.add_parser("changelog", help="insert a release section into CHANGELOG.md")
    changelog_cmd.add_argument("--version", required=True)
    changelog_cmd.add_argument("--notes", required=True, help="markdown file with the release notes")
    changelog_cmd.add_argument("--date", default=datetime.date.today().isoformat())
    changelog_cmd.add_argument("--file", default=str(REPO_ROOT / "CHANGELOG.md"))

    surface_cmd = commands.add_parser("surface", help=argparse.SUPPRESS)
    surface_cmd.add_argument("src")
    surface_cmd.add_argument("output")

    args = parser.parse_args(argv)

    if args.command == "surface":
        Path(args.output).write_text(json.dumps(dump_surface(args.src, json.loads(sys.stdin.read()))))
        return 0

    if args.command == "changelog":
        write_changelog(Path(args.file), args.version, Path(args.notes).read_text(), args.date)
        return 0

    requested = NONE if args.bump == "auto" else LEVEL_NAMES.index(args.bump)
    plan = build_plan(args.head, requested, args.base)
    markdown = render_markdown(plan)
    print(json.dumps(plan, indent=2) if args.json else markdown, end="" if not args.json else "\n")
    if args.summary:
        with open(args.summary, "a") as summary:
            summary.write(markdown)
    if args.github_output:
        with open(args.github_output, "a") as output:
            output.write(f"release={'true' if plan['release'] else 'false'}\n")
            output.write(f"version={plan['version'] or ''}\n")
            output.write(f"previous={plan['base']}\n")
            output.write(f"level={plan['level']}\n")

    if plan["surface_error"] and requested == NONE:
        print(f"error: CLI check failed ({plan['surface_error']}); pass --bump to release anyway", file=sys.stderr)
        return 2
    if args.expect_version and plan["version"] != args.expect_version:
        print(f"error: computed version {plan['version']} != expected {args.expect_version}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
