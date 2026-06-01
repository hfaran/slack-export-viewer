from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("slack-export-viewer")
except PackageNotFoundError:
    __version__ = "unknown"
