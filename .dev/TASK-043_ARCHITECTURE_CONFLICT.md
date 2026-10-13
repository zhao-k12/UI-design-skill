# TASK-043 — ARCHITECTURE_CONFLICT: Penpot 组件绑定的两种原生 ID

日期：2026-10-13。状态：限定于 Adapter 的解析修正，不改 Core 或已冻结的 Registry 快照。

## 当前设计

V0.2.3 的 Penpot `componentReference` 对 Button、Input 保存组件库 ID；对 Select、Table 保存组件主实例 ID。四项绑定均由原生候选和保真验收产生，Core 只传递不解释这些平台 ID。现有 Penpot 运行器却只按组件库 ID 查找。

## 冲突、原因与影响

TASK-043 在创建页面前的宿主预检得到 `missing_native_component: status`。原生读取确认 Select 的绑定 ID `4b3abcb2-3ae8-803f-8008-c8485c8b9729` 指向组件主实例，对应组件库 ID `4b3abcb2-3ae8-803f-8008-c8489b7c9e9a`；Table 同理，绑定主实例 ID `4b3abcb2-3ae8-803f-8008-c85957bd3a28`，组件库 ID `4b3abcb2-3ae8-803f-8008-c8595885b154`。预检在任何 Penpot 写入前中止。若直接把原 ID 当作组件库 ID，页面无法创建；若忽略来源检查，可能实例化错误组件。

## 建议与本次边界

Adapter 在当前文件的本地组件库中精确匹配 `component.id` 或 `component.mainInstance().id`，匹配后统一以真实 `component.id` 核验新实例，同时保持原绑定和保真来源 ID 不变。匹配不到、匹配多个或主实例身份及几何不合格均在写入前失败。新运行脚本另存版本锁，不覆盖 TASK-042 脚本。此修正不改变 UI-IR、Core、组件内容范围和历史 Registry；未来新绑定应规范记录组件库 ID，并另行迁移版本。
