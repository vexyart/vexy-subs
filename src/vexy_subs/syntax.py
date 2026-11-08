# this_file: src/vexy_subs/syntax.py
"""Compatibility import for the shared Audioflexy syntax API."""

import sys

from vexy_audioflexy.speech import syntax

# Keep module identity so existing callers' patches affect engine globals too.
sys.modules[__name__] = syntax
