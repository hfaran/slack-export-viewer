# Release
1) Update `__version__` in `slackviewer/__init__.py` to the new version
2) Commit this change as "Release 0.9.0" to master, as an example
3) Create a release on GitHub with the new version (e.g., 0.9.0) targeting master
4) `git pull` locally
5) `git clean -fdx dist` to clean anything already in the dist/ directory
6) Run  `python setup.py sdist bdist_wheel` (in the correct environment) to create the package to upload
7) Run `twine upload dist/*` to push to PyPI
