# TASK-041 — ARCHITECTURE_CONFLICT: 固定 Table 数据与 Registry/Assembly

日期：2026-10-13。状态：RESOLVED IN V0.2.3 SCOPE。沿用用户已批准的 V0.2 “新增内容范围约束后准入”决策；不扩大到任意表格数据。

## 当前设计

V0.2.2 `contentScope` 仅表达 Button 文本、Input 占位和 Select 选值。`normalize_fixed_native_content` 不识别 Table 的列与行。Assembly 的 `tableRecords` 可携带来源 claim，但未消费为固定原生组件的验收条件。Adapter 只见归一化后的 UI-IR 空 Props/Slots 与固定尺寸，无法判断页面来源是否真的有已验收九格数据。

## 冲突与影响

TASK-040 仅证明三列三行、固定数据和 1392×144 的双平台原生 Table。若直接把 `data.table.default` 标为 active，其他行数据、列配置或缺失来源数据也可能复用同一原生组件，违反 `CONSTRAINTS.md` 第 4、5、11 条。简单地在 Adapter 禁止 Props 并不足以证明 Assembly 来源与固定数据相符。

## 决策与实施边界

在独立 V0.2.3 Registry 增加精确 `columns` 与 `data` 范围，绑定 TASK-040 双平台 Fidelity 报告和原生组件 ID。Assembly 必须逐格读取 `tableRecords` 的来源 claim，与已验收三行数据完全相等，并由已绑定的 Component IR 提供列与几何来源；随后移除内容覆盖，仅输出原生组件引用。Adapter 在写入前重复拒绝 Props、Slots、样式和尺寸覆盖。缺失或不同数据直接失败。V0.1 至 V0.2.2 快照及旧绑定不迁移。
