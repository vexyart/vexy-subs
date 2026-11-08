# this_file: src/vexy_subs/workspace.py
"""Compatibility import for the shared Audioflexy workspace API."""

import sys

from vexy_audioflexy.speech import workspace

# Keep module identity so existing callers' patches affect engine globals too.
sys.modules[__name__] = workspace
