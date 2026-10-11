# Source font file metadata

`font_identity.py` reads bounded SFNT/OTF/TTF/TTC name tables without installing,
uploading or copying font bytes. Unicode and Mac Roman name records are decoded;
unsupported encodings remain explicit. Family/style/PostScript names are paired
within the same platform, encoding and language group. Missing or ambiguous
matches produce REVIEW, with no guessed style or native binding.

```powershell
.venv/Scripts/python.exe -X utf8 component-builder/source-reader/font_identity.py --evidence adapters/figma/metadata/official-runtime-font-evidence.json --system-font "C:/Users/38442/AppData/Local/Microsoft/Windows/Fonts/PingFang SC-Regular.otf" --release-font node_modules/view-ui-plus/dist/styles/fonts/ionicons.ttf --output artifacts/task-009/font-identity/font_file_report.json
```

The actual run identifies PingFang SC / Regular and Ionicons / Regular as inputs
to a read-only Figma load probe. Metadata correspondence does not establish the
browser's loaded file identity. In particular the official TTF is a release
sibling of the browser-served WOFF2, not proof of equivalent rendering. The
reader does not decode WOFF/WOFF2, validate all font tables, approve bindings or
grant Fidelity Gate admission.

The format follows Microsoft's [name table specification](https://learn.microsoft.com/en-us/typography/opentype/spec/name)
and [font-file specification](https://learn.microsoft.com/en-us/typography/opentype/spec/otff).
