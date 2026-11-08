# this_file: src/vexy_subs/qwen.py
"""Compatibility import for the shared Audioflexy qwen API."""

import sys

from vexy_audioflexy.speech import qwen

# Keep module identity so existing callers' patches affect engine globals too.
sys.modules[__name__] = qwen
