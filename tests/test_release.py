"""Tests for scripts/release.py, which decides the next release version."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "release.py"
_spec = importlib.util.spec_from_file_location("release_script", SCRIPT)
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)

NONE, PATCH, MINOR, MAJOR = release.NONE, release.PATCH, release.MINOR, release.MAJOR


@pytest.mark.parametrize("subject, body, expected", [
    ("feat: lazy loading images (#219)", "", (MINOR, "feat")),
    ("fix(cli): handle empty DMs", "", (PATCH, "fix")),
    ("perf: cache channel lookups", "", (PATCH, "perf")),
    ("refactor!: drop --skip-dms", "", (MAJOR, "refactor")),
    ("feat(export)!: rename ARCHIVE_DIR", "", (MAJOR, "feat")),
    ("docs: update README", "", (NONE, "docs")),
    ("ci: update checkout and setup-python (#248)", "", (NONE, "ci")),
    ("Render text of section and header blocks (#254)", "", (NONE, None)),
    ("Bugfix: revert default value for DM's", "", (NONE, None)),
    ("fix: tweak flags", "BREAKING CHANGE: --foo is gone", (MAJOR, "fix")),
    ("Rework flags", "* details\n\nBREAKING-CHANGE: --foo is gone", (MAJOR, None)),
])
def test_classify_commit(subject, body, expected):
    assert release.classify_commit(subject, body) == expected


@pytest.mark.parametrize("level, expected", [
    (NONE, (4, 0, 1)), (PATCH, (4, 0, 2)), (MINOR, (4, 1, 0)), (MAJOR, (5, 0, 0)),
])
def test_bump(level, expected):
    assert release.bump((4, 0, 1), level) == expected


@pytest.mark.parametrize("spec, expected", [
    (">=3.12", (3, 12, 0)),
    ("^3.12", (3, 12, 0)),
    (">=3.8,<4", (3, 8, 0)),
    ("^3.9 || ^4.0", (3, 9, 0)),
    ("<4", None),
    (None, None),
])
def test_python_floor(spec, expected):
    assert release.python_floor(spec) == expected


def meta(python=">=3.12", **deps):
    return {"version": "1.0.0", "python": python, "dependencies": deps, "scripts": {}}


def levels(changes):
    return sorted({level for level, _ in changes})


def test_metadata_python_raise_is_major():
    assert levels(release.diff_metadata(meta(">=3.12"), meta(">=3.13"))) == [MAJOR]
    assert levels(release.diff_metadata(meta(None), meta(">=3.12"))) == [MAJOR]
    assert levels(release.diff_metadata(meta(">=3.12"), meta(">=3.11"))) == [MINOR]


def test_metadata_dependency_changes_are_patch():
    old, new = meta(flask=">=3.0.0"), meta(flask=">=3.1.0", click="*")
    assert levels(release.diff_metadata(old, new)) == [PATCH]
    assert release.diff_metadata(old, old) == []


def opt(*opts, **fields):
    param = {
        "kind": "option", "name": opts[-1].lstrip("-").replace("-", "_"), "opts": sorted(opts),
        "type": "StringParamType", "choices": None, "required": False, "multiple": False,
        "nargs": 1, "is_flag": False, "envvars": [], "default": "None",
    }
    param.update(fields)
    return param


def arg(name, **fields):
    return opt(name, kind="argument", name=name, opts=[name], required=True, **fields)


def surface_levels(old_params, new_params):
    return levels(release.diff_surface({"sev": old_params}, {"sev": new_params}))


@pytest.mark.parametrize("old, new, expected", [
    # unchanged, including a rename of the Python parameter name only
    ([opt("--port")], [opt("--port", name="listen_port")], []),
    # removals and incompatible changes
    ([opt("--port")], [], [MAJOR]),
    ([opt("-p", "--port")], [opt("--port")], [MAJOR]),
    ([opt("--port", type="IntParamType")], [opt("--port", type="StringParamType")], [MAJOR]),
    ([opt("--port")], [opt("--port", required=True)], [MAJOR]),
    ([opt("--x", is_flag=True)], [opt("--x", is_flag=False)], [MAJOR]),
    ([opt("--x", envvars=["SEV_X"])], [opt("--x", envvars=["SEV_Y"])], [MINOR, MAJOR]),
    ([opt("--mode", type="Choice", choices=["a", "b"])],
     [opt("--mode", type="Choice", choices=["a"])], [MAJOR]),
    ([], [opt("--new", required=True)], [MAJOR]),
    ([arg("archive_dir")], [arg("archive")], [MAJOR]),
    # additions and default changes
    ([], [opt("--since")], [MINOR]),
    ([opt("--port")], [opt("-p", "--port")], [MINOR]),
    ([opt("--x")], [opt("--x", envvars=["SEV_X"])], [MINOR]),
    ([opt("--show-dms", "--no-show-dms", default="False")],
     [opt("--show-dms", "--no-show-dms", default="True")], [MINOR]),
    ([opt("--x", required=True)], [opt("--x")], [MINOR]),
    # a computed default is opaque, so swapping it for envvar= is not counted
    ([opt("--archive", default=release.COMPUTED)],
     [opt("--archive", envvars=["SEV_ARCHIVE"], default="None")], []),
])
def test_diff_params(old, new, expected):
    assert surface_levels(old, new) == expected


def test_diff_surface_commands():
    old = {"sev-cli": [], "sev-cli clean": [], "sev-cli export": []}
    new = {"sev-cli": [], "sev-cli export": [], "sev-cli serve": []}
    changes = release.diff_surface(old, new)
    assert (MAJOR, "command `sev-cli clean` removed") in changes
    assert (MINOR, "command `sev-cli serve` added") in changes


def test_surface_of_this_checkout():
    scripts = release.package_metadata((release.REPO_ROOT / "pyproject.toml").read_text())["scripts"]
    surface = release.surface_of_tree(release.REPO_ROOT, scripts)
    assert {"slack-export-viewer", "slack-export-viewer-cli", "slack-export-viewer-cli export"} <= surface.keys()
    archive = next(p for p in surface["slack-export-viewer"] if "--archive" in p["opts"])
    assert archive["opts"] == ["--archive", "-z"]
    assert archive["required"] is True
    assert archive["envvars"] == ["SEV_ARCHIVE"]


def test_write_changelog(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(f"# Changelog\n\nIntro.\n\n{release.CHANGELOG_MARKER}\n")
    notes = "## What's Changed\n* Fix a thing by @someone in #1\n\n**Full Changelog**: x...y\n"
    release.write_changelog(path, "1.0.0", notes, "2026-01-01")
    release.write_changelog(path, "1.0.1", "## What's Changed\n* Another\n", "2026-02-01")
    assert path.read_text() == (
        "# Changelog\n\nIntro.\n\n"
        f"{release.CHANGELOG_MARKER}\n\n"
        "## 1.0.1 (2026-02-01)\n\n### What's Changed\n* Another\n\n"
        "## 1.0.0 (2026-01-01)\n\n### What's Changed\n* Fix a thing by @someone in #1\n\n"
        "**Full Changelog**: x...y\n"
    )


def test_write_changelog_requires_marker(tmp_path):
    path = tmp_path / "CHANGELOG.md"
    path.write_text("# Changelog\n")
    with pytest.raises(SystemExit):
        release.write_changelog(path, "1.0.0", "notes", "2026-01-01")
