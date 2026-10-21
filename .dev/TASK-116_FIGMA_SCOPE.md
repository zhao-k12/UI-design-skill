# TASK-116 — current development is Figma-only

Decision: the user explicitly set the entire Penpot line aside on 2026-10-21. This supersedes the dual-platform target for **active work**, without rewriting historical V0.1/V0.2 evidence or claiming the original dual-platform release has passed.

Scope: keep the nine-stage platform-independent Core, the approved V0.2.6 input and seven-component admission boundary; add a Figma-only production entry. It requires only a Figma file, runs only the Figma preflight, and writes a one-platform Adapter byte lock accepted by the existing verified-script exporter. It does not create a Penpot plan or count any Penpot gate in the current workflow. Historical dual-platform entry and evidence remain archived.

Architecture conflict: `CONSTRAINTS.md` #12 and the original V0.2 plan describe two Adapter versions and dual release validation. The approved input manifest still records the historical Penpot version; the current entry does not read that value or execute Penpot. The current milestone is named `FIGMA_ONLY`, not the original dual-platform V0.2 release. This explicit user decision permits this scoped entry and avoids silently weakening the earlier release definition.

Acceptance: `scripts/run_figma_pipeline.py` on `examples/user-management-compact-search-v026` executes nine Core stages, yields Figma preflight PASS and a Figma-only lock, with no Penpot preflight. Repeating the run is stable; lock drift is rejected as `MIGRATION_REQUIRED`; the verified native script exporter accepts the lock. The Figma platform lock matches TASK-110's previously native-executed, nine-gate-validated page byte for byte, so the existing Figma native evidence remains applicable to this exact plan and Adapter source. This TASK-116 run itself is only a preflight and does not claim a new native execution.

Validation: `tests/test_figma_only_pipeline.py` and `tests/test_v02_pipeline_profile.py`: 5 passed. Existing dual-profile regression remained green. The current run is `artifacts/task-116/figma-only-run`.
