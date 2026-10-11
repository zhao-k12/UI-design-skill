# Section component swap (TASK-015, not natively accepted)

`section_swap.js` adds `swapPenpotSectionComponent` alongside the unchanged
TASK-010 runtime and TASK-015 content executor. It uses the public SDK
`Shape.swapComponent(LibraryComponent)` API, documented in the inspected
`@penpot/plugin-types@1.4.2` declarations. Availability on the active native
host must still be verified; an absent method rejects before mutation.

Inputs are a compiled admitted-component payload, the owned execution ledger,
an explicit single target request, and an independent before capture from
`capturePenpotSectionPatch`. The capture must match the full current root
snapshot and revision. A target must be a genuine linked copy inside a declared
Section, owned by this execution, with the expected old component reference.
The new master must be a real local main instance with exactly matching dimensions;
the translated layout must specify those fixed dimensions. This increment rejects
content overrides and changed source sizes, rather than silently resizing.

After swapping, the copy root ID, parent, name and world geometry must remain
exactly unchanged. The new component link must match, the source master must
remain untouched, and every node outside the old/new instance descendants must
remain unchanged. Descendant IDs may legitimately change and are reported as
created/removed. No page, Section or replacement widget is drawn by this helper.

Preflight failures throw without writes. A failure after the SDK mutation returns
FAIL/PARTIAL, recoveryRequired and before/after snapshots. It does not attempt a
second swap or claim that child IDs can be restored. Success reports SWAPPED with
finalAcceptance NOT_RUN. This is execution status, not fidelity admission.

Remaining: install this execution path through the existing authorized plugin,
perform a native Input-to-Select swap, independently capture the result and full
native PNG, verify source geometry/styles/content and unchanged surrounding
regions, record visual review, then bind those receipts into a proof manifest.
Unit API doubles are not evidence of platform execution or TASK-015 completion.
