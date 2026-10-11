# TASK-014 — Component Resolver and Annotation

AI reads field semantics, data structure, prototype appearance and context, then
records an explicit intent, confidence, rationale and source evidence for each
semantic item. It can request a logical component/variant, never a platform ID.
The closed `component-decisions.schema.json` binds decisions to the current
layout and registry hashes. The program re-runs structure and layout gates,
checks complete item coverage and evidence, then queries the admitted registry.
It does not infer intent from a label alone or call an external model provider.

High confidence resolves an explicit admitted compatible component or a unique
compatible candidate, preferring block, then composite, then base tiers. Missing
high-confidence preferred components remain Missing. Multiple candidates of the
same tier remain Review. Medium confidence can fall back to a unique admitted
standard base component with the same semantic capability; hierarchy/location/
date-range are never downgraded to Input or Select. Low confidence stays Review.
Undeclared variants, planned/deprecated entries and unsupported capabilities do
not produce guessed components. Missing rows expose `missing_component`.

Current intents: text/Input, choice/Select, hierarchy/TreeSelect,
location/Cascader, date-range/DateRangePicker, action/Button, records/Table,
static/Text. The last four complex/static capabilities may lack admitted entries;
this is a reported resource gap, not permission to create one. This first version
does not implement composition-based fallback because slot assembly is TASK-015.
AI must set explicit preferences for visual variants such as primary/default
buttons; capability matching alone does not prove the right visual treatment.

```powershell
.venv/Scripts/python.exe -m core.component-resolver.resolver examples/layout-builder-contract/prototype_analysis.json examples/layout-builder-contract/page_tree.json examples/layout-builder-contract/layout-plan.json examples/component-mapping-contract/decisions.json --source-root examples/prototype-semantic --review examples/layout-builder-contract/synthetic-review.json --output-dir artifacts/task-014/contract --allow-test-fixtures
```

Outputs: component_mapping.json and component_annotation.html. The HTML draws
colored diagnostic labels at the computed Skeleton rectangles and lists logical
IDs and rationale. Colors stay exclusively in the view, never in design tokens or
mapping data. Text is escaped; the view has no executable script or external
asset request. It is a check view, not native component instances/final design.

By default any failed prior gate blocks mapping. Explicit fixture mode permits
diagnostic inspection only when geometry QA passes and test measurements are
declared. It always leaves readyForAssembly=false. Test receipt is synthetic, not
human authorization. A production mapping is eligible only when current upstream
gates pass, every item resolves and the registry is production. TASK-015 must
recompute mapping against current inputs; persisted status alone is insufficient.
