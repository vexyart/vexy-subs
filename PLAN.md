<!-- this_file: PLAN.md -->
# Release follow-up

1. **Publish the provider.** The Audioflexy maintainer needs to publish the wheel and source archive from the v1.0.3 GitHub release through Trusted Publishing. Compare each file’s SHA-256 with its GitHub release asset. The PyPI project currently returns HTTP 404.
2. **Verify the current installation.** Once the provider is available, install `vexy-subs==1.0.7` from PyPI in a fresh environment. Run `vexy-subs version`, `vexy-subs doctor` and `vexy-subs models` and check that the commands find the installed provider.
3. **Decide the 1.0.6 backfill.** The original wheel and source archive are on GitHub. Ask the release owner whether to publish this older version now that 1.0.7 is on PyPI. If approved, upload the preserved pair through Trusted Publishing once Audioflexy is available. Compare both registry hashes with the GitHub assets and exercise the installed CLI.
