# Component Library 0.3.0

TASK-020 adds exactly two frozen official headed Tables to the unchanged 0.2.1 catalog: two columns / two records (720×134.875) and four columns / four records (960×230.875). Native PNGs are 720×135 and 960×231. Both Figma and Penpot have complete fidelity reports and independently verified linked instances.

Select this release explicitly:

```python
from adapters.headed_component_library import load
registry, bindings = load('0.3.0')
```

Logical IDs:

- `data.table.headed.613acb453dafc1629920ac3d697c42918bef2d556cc6f7e61648523f1f7f24aa`
- `data.table.headed.5eca5bc513698ad31a2d57d0660cebee6ef0536e196c5ed468f8153f52b90c25`

These components have no writable slots. Changing titles, records, columns, fonts or geometry requires new official extraction and admission. Keep the exact source dimensions; do not stretch to a layout cell. New tasks still require prototype approval, layout, component mapping, UI-IR validation and actual adapter acceptance.

Use the existing Figma `adapters.figma.compiler.prepare` and Penpot `adapters.penpot.configurable_table_compiler.prepare` with this registry and its bindings. Penpot additionally needs `adapters/penpot/metadata/component-library-0.3.0/native-fidelity.json`. Both paths have passed preflight for both frozen configurations. This does not change the native payload ABI or any prior task's version lock.

The dedicated loader verifies every manifest-bound source, program, capture, proof, report and binding, then checks the versioned registry. The old default catalog and `adapters.component_library_versions.load('0.2.1')` retain their original bytes and behavior. No `latest` alias or automatic migration is provided.

The approved TASK-020 decision governs only these two configurations. Exact fonts, glyph encodings, baselines, native geometry and paint, independent vectors, raw PNG alpha, positive-area pixel ownership, edge bands, complete horizontal coverage and retained glyph paint are required. Penpot header backgrounds are the proven same-color source-cell union. Raw native PNGs remain unmodified. Full evidence is under `evidence/{figma,penpot}/{two-column,four-column}/`; actual capture and instance records remain in Adapter Metadata.
