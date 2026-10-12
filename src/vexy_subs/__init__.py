# this_file: src/vexy_subs/__init__.py
"""Speaker-coloured local subtitles."""

try:
    from .__version__ import __version__
except ImportError:  # Source checkout without a build: ask installed metadata.
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("vexy-subs")
    except PackageNotFoundError:
        __version__ = "0.0.0"
