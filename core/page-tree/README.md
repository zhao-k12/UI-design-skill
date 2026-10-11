# TASK-012 — Page Tree and Structure QA

The builder maps each observed block to one semantic Section, preserving block
order, item category order, descriptions and evidence. It invents no header,
pagination, component, geometry or layout. The current analysis contract contains
one page; multiple-page contracts are not yet supported.

```powershell
.venv/Scripts/python.exe -m validators.structure.gate examples/prototype-semantic/prototype_analysis.json --source-root examples/prototype-semantic --output-dir examples/prototype-semantic/structure
```

The command saves `page_tree.json` and `structure_qa_report.json`; exit 0 means
PASS, exit 1 means Review or FAIL. A draft tree can be inspected on Review/FAIL,
but it cannot proceed to layout. Malformed analysis fails before construction.

The independent validator rechecks original source bytes, evidence quotes and
analysis fingerprint. It compares page identity/task, ordered Sections, every
field/button/data region/static item, categories, descriptions, evidence and
unique IDs. Closed schemas reject nested Sections, child-bearing leaves, visual
properties and platform metadata. Omission means omission relative to the
analysis, not automatic detection of things the AI missed in the original image.
That remains part of semantic review.

`--review path/to/review.json` accepts a human review receipt conforming to
`schemas/prototype-review.schema.json`. Approval is bound to the full canonical
analysis SHA-256. Unresolved questions still block PASS. The parser's original
Review artifact is immutable: review is separate, never achieved by rewriting
`status` or `readyForStructure`. Receipt identities are declarations, not digital
signatures; the caller must obtain and retain actual human authorization. Tests
use explicitly synthetic receipts, which are not production approvals.

Only a recomputed PASS report contains `freeze`, binding tree and analysis hashes.
Consumers must rerun the gate on current source/analysis/tree/review before use;
editing the tree, replacing a source, or changing a receipt invalidates the
previous report. Persisted PASS text alone is not authorization to run layout.
The TASK-013 layout consumer is not implemented in this task.
