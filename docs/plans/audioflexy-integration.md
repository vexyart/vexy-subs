<!-- this_file: docs/plans/audioflexy-integration.md -->
# Audioflexy inference integration

## Objective and Global Constraints
Replace vexy-subs local model execution with importable vexy-audioflexy APIs; port missing functionality into Audioflexy. Preserve current dirty owner changes, all backend choices, hints/reference safeguards, lexical/timing validation, native identities, stage resume, error propagation, offline rendering and subtitle output. No weights, private inputs, identifying runtime evidence or machine paths enter public artifacts. No publication or model storage migration is required. Keep model imports lazy and model dependencies optional. Reuse source implementations rather than designing new model adapters. Independent review must assess the complete change.

## Task 1: Reusable Audioflexy model APIs
Ownership: vexy-audioflexy repository only. Port current subs qwen, inference, alignment, audiocpp and punctuation model functionality into a small importable speech package with validated neutral Word/Turn types. Move necessary pure vocabulary/metadata/excerpt helpers without adding subtitle parser dependencies. Preserve all current source behavior, especially dirty Qwen retry/drop and reference handling. Provide legacy workspace execution through packaged Audioflexy adapters rather than requiring the old incoming tree. Retain user-supplied workspace compatibility if practical but no duplicated model implementation. Move langid identification and NLTK tagging model operations into library APIs too; editorial layout stays in subs. Use optional apple/native/cluster/editorial dependency groups, lazy imports, no mandatory heavy stack. Native and workspace compatibility environment settings must continue working; Audioflexy can accept its own equivalent settings as well. Add focused meaningful tests by reusing the existing speech regression cases and neutral APIs, with isolated engine fakes. Update Audioflexy README, DEPENDENCIES, WORK, CHANGELOG and integration PLAN/TODO entries. Do not alter unrelated adapters or release behavior. Run full Audioflexy tests and build an installable wheel.

## Task 2: Replace subtitle local inference and verify integration
Ownership: vexy-subs repository. Depend on vexy-audioflexy and route all local speech/language/POS model operations to its APIs. Delete replaced engine implementation; retain thin compatibility imports only where necessary. Keep Word/Turn identity and mutation semantics by sharing library types or explicit safe adapters. Update pipeline, CLI doctor/models, backend/workspace routes, cache implementation identity, extras, lockfile, tests, README and affected docs/skills/DEPENDENCIES. Preserve subtitle rendering/editorial logic and owner changes. Source checkout development may use uv source override; wheel metadata must use a portable package dependency, never a local absolute path. Document installation from two local wheels if the needed Audioflexy version is unpublished. Run complete subs tests and checks; build both packages; clean-install exact wheels outside both trees and run realistic synthetic end-to-end inference/export/resume and offline CLI/render checks. Run real available MLX/native smoke inference with public/synthetic audio and record actual acceptance limits privately. Review the combined diff independently and resolve material findings. Record completion evidence and remaining limitations in WORK/PLAN/TODO/CHANGELOG.


## Implementation evidence — 2026-11-08

Task 1 is implemented and independently accepted. Task 2 source integration,
source tests (149 passed, 91.68% consumer coverage, Ruff clean), strict docs,
four package archives, portable metadata/privacy audit and fresh Python 3.12
base-only two-wheel synthetic integration/export/resume/offline CLI checks pass.
Engine fakes replace only model loading/generation inside actual provider APIs.
Provider speech bytes/runtime versions identify inference; punctuation identity
is separate; language/POS implementation/runtime identity affects editorial
receipts only. Existing owner changes and backend contracts are preserved.
Controller real source inference/export/resume passed. Installed real-model/PATH
checks and separate-process resume passed; final independent combined review
remains a separate acceptance gate.
The local native binary's `nemotron_3_diar` rejection remains an explicit runtime
compatibility limitation. No publication or model-storage migration is included.
