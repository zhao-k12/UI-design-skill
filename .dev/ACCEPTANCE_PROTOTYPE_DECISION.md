# First end-to-end prototype decision

Date: 2026-10-08, Asia/Shanghai.

The human user selected: “采用已验收列表页的‘姓名／状态／角色’，将其冻结为首次验收原型”.
This resolves the conflict with the earlier authored semantic fixture whose table
columns were 姓名／邮箱／状态. That earlier fixture remains intact and is not silently
reinterpreted as this prototype.

The authoritative first static list is the original TASK-009/TASK-010 accepted
UI-IR, `examples/adapter-fidelity-acceptance.ui-ir.json`, with its source-bound
Table body and original captures. TASK-015 mutation examples are independent
fixtures and do not redefine this baseline. In particular, the canonical query
button remains 查询, the name control remains Input, and the selected state is 启用.

`examples/acceptance-prototype/prototype.txt` is a text transcription of these
known static contents, including the two admitted Remix icons and three existing
Table rows. The frozen manifest binds its bytes, the source UI-IR, native PNGs and
Table Component IR. Static acceptance covers the visible selected state and does
not require inventing a dropdown option list or business interactions.

This decision supplies the prototype choice. Subsequent semantic, structure,
layout, assembly, resource and release checks still must actually execute; it is
not a Release Gate PASS or permission to fabricate missing resources.
