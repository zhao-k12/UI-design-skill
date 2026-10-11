# TASK-014 acceptance — 2026-10-08

Actual CLI execution generated component_mapping.json and component_annotation.html
under examples/component-mapping-contract, using the existing explicitly synthetic
layout fixture and the real production catalog/fidelity reports. The fixture
contains no user approval and is not eligible for production assembly.

All nine source items are represented exactly once. Seven resolve: one Input,
one Select, four Buttons and one Table. Two static items report Missing because
Text is not registered; no temporary component, platform object or fake fidelity
record was created. Missing rows preserve intended capability and evidence.
The mapping status is Missing and readyForAssembly=false.

Opened the actual HTML through the in-app browser, verified the colored Input,
Select, Button and Table areas, both missing text areas, logical ID table, rationale,
fixture notice and blocked assembly notice. Saved annotation-review.png. The
viewport shows the same computed rectangles; horizontal scrolling accommodates
the 1440px layout. Colors are only diagnostic. This is not a platform design.

Tests cover real registry resolution, Missing, low-confidence Review, medium
same-capability fallback, rejection of lossy hierarchy/location/date-range fallback,
unready high-confidence preferred entries, stale hashes, omissions, duplicates,
unrelated evidence, incompatible semantic category/component, unknown fields,
upstream gate rejection, unchanged inputs and HTML escaping. A registered-only
synthetic fixture tests PASS while still blocking formal assembly. No registered
component source or fidelity policy was modified.

Full regression and final targeted checks are recorded in DEVELOPMENT_STATE.md.
TASK-015 instance assembly/content injection has not been implemented in this task.
