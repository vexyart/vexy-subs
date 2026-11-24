<!-- this_file: WORK.md -->
# Work record

## 2026-11-24

- PyPI serves the vexy-subs 1.0.7 wheel and source archive. Their SHA-256 hashes match the v1.0.7 GitHub release. PyPI’s attestations identify `vexyart/vexy-subs`, `release.yml` and the `pypi` environment.
- PyPI returns HTTP 404 for vexy-audioflexy and vexy-subs 1.0.6. A PyPI-only `uv pip install --dry-run` for 1.0.7 failed because it could not resolve `vexy-audioflexy[editorial]>=1.0.3`. The registry installation check and the decision on the preserved 1.0.6 archives remain in PLAN.md.
- The public home, installation and development pages returned HTTP 200. The installation page documents the Audioflexy requirement.
- Local verification with fly-january 0.2.1: `./build.sh docs` built 14 HTML pages in strict mode with zero warnings. `UV_NO_SYNC=1 ./test.sh` passed 149 tests with 91.68% coverage and Ruff clean using the local Audioflexy installation.
