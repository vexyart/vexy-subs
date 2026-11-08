# this_file: src/vexy_subs/inference.py
"""Compatibility import for the shared Audioflexy inference API."""

import sys

from vexy_audioflexy.speech import inference

# Keep module identity so existing callers' patches affect engine globals too.
sys.modules[__name__] = inference
