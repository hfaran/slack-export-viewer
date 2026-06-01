# Release
1) Update `version` in `pyproject.toml` to the new version
2) Commit this change as "Release 4.1.0" to master, as an example
3) Create a release on GitHub with the new version (e.g., 4.1.0) targeting master

## Build and Publish

### Automated

4) Ensure the deploy GitHub Action succeeds, or

### Manual

4) `git pull` locally to get the tagged release commit
5) `poetry install` to sync the environment
6) `git clean -fdx dist` to remove any stale build artifacts
7) `poetry build` to produce the sdist and wheel under `dist/`
8) `twine upload dist/*` to push to PyPI
   - Requires a PyPI API token — either set `TWINE_PASSWORD=<token>` and `TWINE_USERNAME=__token__` in your environment, or configure `~/.pypirc`
   - Alternatively, `poetry publish` can replace this step if you have a token configured via `poetry config pypi-token.pypi <token>`
