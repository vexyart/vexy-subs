# this_file: src/vexy_subs/punctuation.py
"""Compatibility import for the shared Audioflexy punctuation API."""

import sys

from vexy_audioflexy.speech import punctuation

# Keep module identity so existing callers' patches affect engine globals too.
sys.modules[__name__] = punctuation
