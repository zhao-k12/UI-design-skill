# TASK-013 — Layout Tree Builder

This entry point connects a source-bound Page Tree to the TASK-004 deterministic
engine. The structure gate is recomputed using original source bytes, analysis,
tree and a separate semantic review receipt before any layout is generated.

AI supplies `layout-plan.schema.json`: choose one of the five standard patterns
and map each semantic Section to exactly one distinct region supported by that
pattern. Ambiguous, duplicate, missing or extra assignments fail rather than
guess. The current version supports at most one Section per region. Unused
template regions are omitted; no invented header or pagination content is added.
Pattern order is explicit and may differ from observation order; source IDs
preserve the correspondence. AI must review those region assignments as part of
the design judgment, not claim the builder has inferred them automatically.

The versioned project rules use a 24 Grid, field span 6, field gap spacing.md,
button gap spacing.sm, section gap spacing.section and page padding spacing.page.
Fields use inner Grids and buttons use HorizontalStacks. Full-width groups in
query/form/metrics span 24. This is project layout policy, not an extracted
official component geometry. No component is chosen and no free coordinate is
accepted. All semantic items map exactly once to measured Cells; all Sections
and the page retain source IDs.

Measurements use the existing engine contract (runtime/test-fixture plus a
source reference); they are supplied, not inferred from text. Their accuracy is
the caller's responsibility. The whole plan, tree, rules and token registry are
hash-bound in QA. This is not a component fidelity gate. Runtime measurement
evidence must be retained by the caller; a reference string alone does not prove
a real browser measurement. Test measurements require `--allow-test-fixtures`
and always force readyForMapping=false, even when geometry QA passes.

```powershell
.venv/Scripts/python.exe -m core.layout.builder examples/layout-builder-contract/prototype_analysis.json examples/layout-builder-contract/page_tree.json examples/layout-builder-contract/layout-plan.json --source-root examples/prototype-semantic --review examples/layout-builder-contract/synthetic-review.json --output-dir artifacts/task-013/contract --allow-test-fixtures
```

This command demonstrates a synthetic contract fixture, not user approval or a
production design. Its geometry QA is PASS but process exit is 1 because mapping
is blocked for test measurements. It writes layout_tree.json and
layout_qa_report.json, including engine Skeleton and diagnostics. Structure
Review/FAIL writes null layout_tree.json, replacing a stale successful output.
Layout failure keeps the invalid draft for diagnosis, with null engine Skeleton.
Only readyForMapping=true can enter TASK-014; downstream consumers must rerun
generation on current inputs rather than trust an edited/old report.

The pre-existing user-management semantic example has unresolved questions and
no human approval. Its saved layout result correctly remains Review/null.
