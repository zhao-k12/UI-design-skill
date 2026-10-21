# TASK-120 — one-call native read of 18 Figma masters

Scope: improve component QA throughput without changing any admitted master, user page, Registry, Core, or Adapter runtime. The user approved batching while preserving output quality. Penpot remains deferred. Formal page generation still goes through UI-IR; this task creates no page.

`scripts/prepare_figma_batch_master_read.py` compiles `scripts/figma_batch_master_read.js` against the V0.2.7 Figma binding and Registry. It verifies the 18 logical IDs, variants, component references and fidelity-report hashes before generating a read-only host script. The template lives outside `adapters/figma` so this QA tool does not alter the locked Adapter runtime bytes.

One `use_figma` call read all 18 existing native masters by ID in the target file. It returned component identity, page, dimensions and visible text properties; no nodes were created or changed. The independently stored result is `artifacts/task-120/figma-live-masters.json`; a committed evidence fixture is `tests/fixtures/figma-v027-batch-master-read.json`. `scripts/audit_v027_figma_batch_masters.py` checks every row against the immutable Registry and bindings. Result: 18/18 PASS, zero issues. Tampered text, ID and width fail their affected rows.

The first native batch request encountered a transient Figma transport failure. A connection check succeeded and the subsequent request completed. The host script preparation is reproducible; its hash is in `artifacts/task-120/prepared/batch-master-preparation.json`. The existing Figma-only release's ten gates remain PASS. This work accelerates readback of admitted masters; it does not create new variants or replace their official-source and visual fidelity checks.
