# TASK-114 — V0.2.6 已审核输入迁移防覆盖

日期：2026-10-20。状态：**PASS / V0.2_NOT_READY**。

`scripts/migrate_compact_search_v026.py` 现在在目标输入包已存在时先核对来源副本、人工审核语义、Registry 决策、组件库版本、内容映射和逐文件哈希；完全一致则返回 `REUSED`，不写文件。目标内容有差异时明确拒绝覆盖，包括修改内容后同步改写 input-manifest 哈希的情况。新目标仍按已批准来源生成，随后以同一检查自验并返回 `CREATED`。

测试在隔离目录新建、重复运行和篡改目标；新建包与已验收 V0.2.6 包逐文件字节一致，篡改被拒绝且目标字节保留。相关回归 7 项 PASS。[当前就绪重算](../artifacts/task-114/current-release-readiness.json)仍为 `evidenceValid=true`、`releaseReady=false`。历史输入和原生证据均未覆盖。
