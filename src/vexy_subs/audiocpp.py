# this_file: src/vexy_subs/audiocpp.py
"""Compatibility import for the shared Audioflexy audiocpp API."""

import sys

from vexy_audioflexy.speech import audiocpp

# Keep module identity so existing callers' patches affect engine globals too.
sys.modules[__name__] = audiocpp
