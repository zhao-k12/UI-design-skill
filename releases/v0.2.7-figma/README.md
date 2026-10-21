# V0.2.7 Figma fixed-scope profile

This profile admits 18 fixed native component configurations backed by official View UI Plus runtime captures and independent Figma QA. The new 11 configurations were admitted in one versioned batch; V0.2.6 remains immutable. The fixed scope locks source props, native visible text and dimensions. Other props, text, size or state combinations require a separate admission.

Run the approved compact-search sample with `scripts/run_figma_pipeline.py`, input `examples/user-management-compact-search-v027-figma` and profile `v0.2.7-figma`. The resulting plan is tied to the Figma Adapter byte lock. The verified sample was executed on Figma page `252:1244` in file `0vGWSRoLxBiVPXiZ8xJAX9`; independent readback, full-size repeated PNG and all 10 scoped gates passed. The sample uses four component types; the other 14 were verified as native masters during admission.

Evidence and current gate results: `artifacts/task-118/figma-release-gates.json`. Historical dual-platform V0.2 release status is separate.
