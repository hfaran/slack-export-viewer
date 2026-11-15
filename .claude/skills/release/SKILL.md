---
name: release
description: Preview and cut a slack-export-viewer release. Computes the next semver version from code changes and commit titles since the last tag, shows the plan, and after confirmation dispatches the Release GitHub workflow and watches it through to PyPI.
argument-hint: "[patch|minor|major]"
disable-model-invocation: true
---

# Release slack-export-viewer

`scripts/release.py` decides the version, not you. Your job: show its plan, give an
advisory read of commits it could not classify, get the user's confirmation, dispatch
the Release workflow, and report the outcome. Nothing is pushed or published until the
user confirms in step 3.

## 1. Plan against origin/master

The workflow releases `origin/master`, so plan against that, not the local checkout.
Requested level: "$ARGUMENTS". Use it as `<level>` below if it is patch, minor or major;
otherwise use `auto`.

```sh
git fetch origin master --tags
poetry run python scripts/release.py plan --head origin/master --bump <level>
```

Show the plan to the user as-is. If it says there is nothing to release, stop and say so;
mention they can force one with `/release patch`. If the CLI check failed (exit code 2),
show the error and ask which level to use before going further.

## 2. Advisory review of unclassified commits

Skip this if the plan lists no commits with "no conventional type".

For each of those commits, read it (`git show --stat <sha>`, then the relevant hunks under
`slackviewer/`). Judge whether a user of the CLI or the generated HTML would see it as:
- a new feature → minor
- a breaking change in behaviour or output → major
- a fix or internal change → no change to the plan

Only ever suggest a level higher than the computed one; the computed level is a floor.
Give each suggestion one line with the evidence (file and what changed).

## 3. Confirm

Use AskUserQuestion with these options:
- "Release X.Y.Z" (the computed plan)
- "Release X'.Y'.Z' as <level>" (only if you suggested a higher level in step 2)
- "Cancel"

For a higher level, re-run the plan with `--bump <level>` and use the version it prints.

## 4. Dispatch and watch

```sh
gh workflow run release.yml --ref master -f bump=<auto|chosen level> -f expected_version=<X.Y.Z>
gh run list --workflow release.yml --event workflow_dispatch --limit 1 --json databaseId,url,createdAt
```

If the newest run was created before your dispatch, list again. Then run
`gh run watch <id> --exit-status` in the background and wait for it to finish.

`expected_version` makes the workflow fail instead of releasing something different from
what the user approved (for example, if master moved since the preview).

## 5. Report

On success, give the version, the GitHub release URL (`gh release view <X.Y.Z> --json url`)
and https://pypi.org/project/slack-export-viewer/<X.Y.Z>/.

On failure, show the failing job and the relevant lines from `gh run view <id> --log-failed`,
and say what already happened:
- failed in `plan` or `test`: nothing changed; fix and run `/release` again
- failed in `release` before "Commit, tag and push": nothing changed
- failed after the push (tag exists): don't dispatch again. Finish by hand: `gh release create`
  if the release is missing, or `gh run rerun <id> --failed` if only `publish` failed
