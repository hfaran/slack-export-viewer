# Release

New: automated release workflow with changelog generation

You can now run a GitHub Actions workflow to perform steps 1–3 (update __version__, commit to branch, create GitHub release) and it will generate a changelog from recent commits and use it as the release body.

1) Use the Actions tab in GitHub, select "Automated release (update version, commit, create release with changelog)" and click "Run workflow". Provide:
   - version: the new version (e.g. 0.9.1)
   - branch: branch to update (default: master)
   - create_release: true/false (default: true)

Or use the GitHub CLI:
  gh workflow run release.yml --repo hfaran/slack-export-viewer -f version=0.9.1 -f branch=master -f create_release=true

What the workflow does:
1) Updates `__version__` in `slackviewer/__init__.py`
2) Commits that change to the specified branch with the commit message `Release <version> [skip ci]`
3) Generates a changelog of commits since the most recent `v*` tag and uses it as the release body
4) Creates a GitHub release with tag `v<version>` targeting the branch

Notes and caveats:
- The changelog generation uses `git log` to list commit messages since the latest `v*` tag. If no previous tag exists, it will include the repository history.
- The workflow uses the built-in token with contents: write permission to push the commit and create the release. That token is provided automatically to workflows; no additional secrets should be required.
- The commit message includes [skip ci] to reduce accidental retriggers of CI that respect this convention.
- If you prefer a draft release, a different changelog format, or to include PR numbers / body text, I can adjust the changelog script to extract more metadata (e.g. reading PR titles or parsing conventional commits).
- Manual build/publish steps remain the same if you need to upload to PyPI manually:
  4) `git pull` locally
  5) `git clean -fdx dist` to clean anything already in the dist/ directory
  6) Run  `python setup.py sdist` (in the correct environment) to create the package to upload
  7) Run `twine upload dist/*` to push to PyPI

# Release (Legacy)
1) Update `__version__` in `slackviewer/__init__.py` to the new version
2) Commit this change as "Release 0.9.0" to master, as an example
3) Create a release on GitHub with the new version (e.g., 0.9.0) targeting master

## Build and Publish

### Automated

4) Ensure the deploy Github Action succeeds, or

### Manual

4) `git pull` locally
5) `git clean -fdx dist` to clean anything already in the dist/ directory
6) Run  `python setup.py sdist` (in the correct environment) to create the package to upload
7) Run `twine upload dist/*` to push to PyPI
