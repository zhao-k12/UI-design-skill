# TASK-015 native content subtask — PASS (2026-10-08)

This is a completed native content subtask, not full TASK-015 completion.

File: 91396aad-60c8-808b-8008-c0885ca79899. Separate acceptance page:
b5a46b76-bcf2-8039-8008-c22ccfb1da66. Execution is derived from the admitted fixed
UI-IR with a distinct document identity. The TASK-010 acceptance page is retained.
The existing installed project plugin was reused without expanding permissions.

The query button copy b5a46b76-bcf2-8039-8008-c22cd1731fbd remains linked to admitted
component 10f3de97-3a09-806f-8008-c0aff4ac5af0. Only its text child
b5a46b76-bcf2-8039-8008-c22cd1731fbf changes from 查询 to 导出. The new caption is a
literal already present in the baseline UI-IR; the scenario is an adapter test.
Button remains 60 × 32 at (1152, 202). No node is created, removed or detached by
the patch. The query region is the only affected region, with 76 other native
nodes exactly unchanged. Native PNG differences are confined to the button box.

Before/patch/after receipts and original PNGs are independently saved in
adapters/penpot/metadata/section-content-acceptance. Native PNG SHA-256:
6597b57ad6725c088f09470bbc2711c309701ca4cfd179d6c08370f151be6bf9.
Visual review confirms complete readable 导出 glyphs and unchanged page content.
Workspace screenshot shows the actual page and dimensions. Current source binding,
native-copy identity, font/style, snapshots, topology and raster bounds all pass.

The initial attempt was rejected before mutation because the legacy region is a
top-level Frame. It now requires an explicit region declaration. First after-PNG
export failed with a server timeout; the failure receipt is retained. A subsequent
independent export completed. Penpot's saved revision advanced from 16 to 17 after
the operation; exact node-snapshot equality and separate capture verification
prevent treating a changed state as the same result.

Full Task acceptance remains false. Core instance placement currently uses Cell
allocation sizes, while native instances require admitted source dimensions; this
must be reconciled without stretching or rebuilding the page. Component-type swaps,
remaining native slots/table headers and the other-platform content path are still
pending. Existing complete semantic fixture remains Review/Missing for upstream
reasons; native adapter testing does not approve that prototype.
