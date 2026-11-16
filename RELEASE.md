# Release

## Automated

The **Release** workflow (`.github/workflows/release.yml`) cuts releases from master.
Start it any of these ways:

- In Claude Code: `/release`. It previews the plan, asks before dispatching, then
  watches the run. `/release minor` sets a minimum level.
- Actions tab → Release → Run workflow.
- `gh workflow run release.yml`. Add `-f dry_run=true` to only see the plan, or
  `-f bump=minor` to set a minimum level.

To preview locally: `poetry run python scripts/release.py plan`

### How the version is chosen

`scripts/release.py plan` compares master with the latest release tag and takes the
highest of these levels:

| Signal | major | minor | patch |
|---|---|---|---|
| CLI (loaded and compared option by option) | command, option, flag spelling or env var removed; option type changed; new required option or argument | command, option, flag spelling or env var added; default changed | — |
| Package metadata | minimum Python raised | minimum Python lowered | dependency added, removed or changed |
| Package files | — | — | anything under `slackviewer/` changed |
| Commit titles | `type!:` or a `BREAKING CHANGE:` footer | `feat:` | `fix:`, `perf:` |
| `bump` input | `major` | `minor` | `patch` |

Help text and type parameters (e.g. `Path()` → `Path(exists=True)`) don't count.
If nothing reaches patch (only docs, tests or CI changed), there is nothing to release.

### PR titles

PRs are squash-merged and the PR title becomes the commit subject, so titles must
follow [Conventional Commits](https://www.conventionalcommits.org/). The **PR title**
check enforces it. Use `feat:` for features that don't add a flag (the CLI check can't
see those), and `!` (e.g. `feat!:`) for changes that break existing usage or output.

### What the workflow does

1. Runs the CI tests and computes the plan (shown in the run's summary).
2. Sets the version with `poetry version`, adds the release notes to `CHANGELOG.md`,
   commits "Release X.Y.Z", tags `X.Y.Z` and pushes both.
3. Creates the GitHub release with GitHub's generated notes (edit them afterwards if
   you like; `CHANGELOG.md` keeps the generated copy).
4. Builds with Poetry and publishes to PyPI.

### PyPI credentials

Both `release.yml` and `python-publish.yml` publish with
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/): PyPI accepts a
short-lived OIDC token from those two workflow files when they run in this repo's
`pypi` environment. No PyPI token is stored in GitHub. The environment only allows
master and `X.Y.Z` tags. If either workflow file or the environment is renamed, update
the publishers in the PyPI project's Settings → Publishing first.

## Manual

1) Update `version` in `pyproject.toml` to the new version
2) Commit this change as "Release 4.1.0" to master, as an example
3) Create a release on GitHub with the new version (e.g., 4.1.0) targeting master

### Build and Publish

#### Automated

4) Ensure the deploy GitHub Action (`python-publish.yml`) succeeds, or

#### Manual

Publishing from your own machine needs a PyPI API token. Only the workflows can publish
without one.

4) `git pull` locally to get the tagged release commit
5) `poetry install` to sync the environment
6) `git clean -fdx dist` to remove any stale build artifacts
7) `poetry build` to produce the sdist and wheel under `dist/`
8) Create an API token at https://pypi.org/manage/account/token/ with the scope
   "Project: slack-export-viewer". Don't use an all-projects token.
9) `poetry publish` to push to PyPI. Give it the token in one of two ways:
   - Store it once with `poetry config pypi-token.pypi <token>`. Poetry keeps it in the
     system keyring when one is available.
   - Pass it for a single run: `POETRY_PYPI_TOKEN_PYPI=<token> poetry publish`

   Delete the token on PyPI when you no longer need it.
