# this_file: src/vexy_subs/alignment.py
"""Compatibility import for the shared Audioflexy alignment API."""

import sys

from vexy_audioflexy.speech import alignment

# Keep module identity so existing callers' patches affect engine globals too.
sys.modules[__name__] = alignment
