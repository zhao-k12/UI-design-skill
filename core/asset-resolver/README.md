# Existing business assets

Supported categories: logo, avatar, photo, banner, illustration, background and
empty-state. The initial production catalog is empty because no business images
were supplied. Assets are explicitly existing PNG/JPEG/WebP static files, with a
logical ID, source reference, relative path, exact byte SHA and original dimensions.
SVG/animated media are outside this version's asset decoder; no image is generated.

Resolution order is an exact prototype asset ID, then the exact registry ID, then
`missing_asset`. A corrupt/mismatched prototype asset fails; it cannot silently
fall back to a different image. Paths must stay within the declared source root,
including after symlink resolution. The file is reread on every resolve, so changed
bytes cannot reuse an old successful registry result. Catalog/outputs are isolated.

UI-IR `resourceIssues` preserves missing_component, missing_icon, missing_asset and
unsupported_component against logical nodes. These documents are schema-valid
diagnostics; `validate_document` still returns their issues and blocks both native
compilers. No missing-image rectangle or fabricated logo is created. A successful
resource report means resources resolved, not native Image support or page fidelity.
Historical adapters still report unsupported Image execution until a declared
native asset mapping is implemented. The frozen first list has no image requirement.

```powershell
.venv/Scripts/python.exe -m core.asset-resolver.resolver examples/adapter-fidelity-acceptance.ui-ir.json --asset-root registries/assets --output artifacts/task-016/resource-resolution.json
```

Optional `--prototype-assets` is a JSON array of asset descriptors; supply its
`--prototype-root`. `--catalog` selects a frozen registry snapshot. CLI emits the
current report and exits nonzero for Missing/Unsupported/FAIL, replacing stale
successful output without overwriting inputs or image source bytes.
