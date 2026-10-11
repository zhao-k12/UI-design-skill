# Prototype semantic parsing — TASK-011

This stage separates AI interpretation from deterministic evidence validation.
It accepts source-bound AI observations and emits `prototype_analysis.json`.
It does not perform OCR, call a model provider, build a Page Tree, select
components, calculate layouts, or approve its own semantic interpretation.

## AI observation workflow

1. Read the supplied static prototype text. For screenshots, first prepare and
   review a UTF-8 transcript; image provenance/OCR automation is not implemented.
2. Describe page identity and primary user task. List functional blocks, fields,
   buttons, data display regions, and static content separately. Empty category
   arrays mean nothing observed in that block; never invent missing items.
3. Follow `schemas/prototype-observations.schema.json`. Give every claim at least
   one evidence reference. Each evidence entry names a source and quotes an exact
   substring with zero-based Unicode character offsets (end exclusive, including
   the decoded source's original CR/LF characters). Hash original source bytes
   with SHA-256; decode UTF-8 with optional BOM for offsets.
4. Preserve ambiguous or missing information as questions in `unknowns` with
   evidence references. Do not infer status options, navigation destinations,
   button behavior, interaction flows, component names, colors, spacing, or grids.
5. Run the parser. Hash mismatch, missing evidence, unknown fields, duplicate IDs,
   outside-root sources, and altered quotes reject output. Existing output is
   never overwritten on validation failure; callers must use the successful
   process result, not assume an old artifact represents the rejected input.
6. Review the semantic meaning against the source. Output remains `Review` and
   `readyForStructure=false`; source quote validity does not prove interpretation.
   Approval and downstream structure orchestration are not implemented here.

```powershell
.venv/Scripts/python.exe -m core.prototype.parser examples/prototype-semantic/observations.json --source-root examples/prototype-semantic --output examples/prototype-semantic/prototype_analysis.json
```

The example is an explicitly authored test prototype, not a readback of a live
design or evidence of automatic screenshot comprehension. It includes a missing
status-option question to demonstrate preservation of uncertainty.
