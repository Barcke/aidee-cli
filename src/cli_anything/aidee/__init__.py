"""Aidee user CLI: personal and explicitly authorized team content."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("cli-anything-aidee")
except PackageNotFoundError:
    __version__ = "2.0.0"
