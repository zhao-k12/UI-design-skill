# TASK-117 — batch review of the 11 remaining Figma candidates

The user identified one-component-at-a-time validation as too slow. This task replaces eleven repeated evidence checks with one deterministic batch audit. The user has already narrowed active development to Figma only (TASK-116). Historical dual-platform admission is not rewritten.

`scripts/audit_figma_candidate_batch.py` audits all 11 existing candidates in one command. For each type it joins the official runtime Component IR, extraction hash, official screenshot, Figma QA, native component metadata, and the independently verified PNG/SVG/readback hashes from the existing coverage audit. It fails the batch on any source, identity, screenshot, QA, or native evidence drift. Its output preserves an individual row and issue list for each component, so batching cannot hide a failed component.

Result: 11/11 evidence rows PASS, 0 issues. Four have explicit fixed content scopes; seven need a fixed-scope contract review before formal production Registry admission. This is a single review queue, not seven separate candidate capture tasks. No candidate is silently promoted: `formalRegistryAdmission=NOT_RUN`.

ARCHITECTURE_CONFLICT for the next step: the current `ComponentRegistry` production gate is hard-coded to the seven historical dual-platform component types and versions. The Figma-only scope decision does not by itself define a new 11-type production admission contract. Recommended migration: add one versioned Figma-only gate, batch-compile all approved fixed scopes and source/native hashes, then register all passing components in one new immutable profile. Keep V0.2.6 and its historical evidence unchanged. This task does not change the Core admission rule.

Acceptance: `artifacts/task-117/figma-candidate-batch.json` records 11 PASS rows and the seven fixed-scope review types. Five targeted tests pass, including a changed official identity rejection. Command:

```powershell
.\.venv\Scripts\python.exe scripts/audit_figma_candidate_batch.py --output artifacts/task-117/figma-candidate-batch.json
```
