# TASK-046 — ARCHITECTURE_CONFLICT: Page 的 Hug 高度与 V0.2 最小画布

日期：2026-10-14。状态：限定 V0.2 静态增高策略的解决方案。

## 当前设计

V0.1 `list-page` Pattern 将 Page 高度设为 `hug`。Layout Engine 仅在求解后验证 `constraints.minHeight`，不会让 Hug 容器扩至最小值；内容少时页面低于 V0.2 目标的 1080。TASK-045 已建立 1920 宽 Token，但尚未改变高度。

## 原因与影响

把 Page 固定为 1080 会令超过一屏的静态内容溢出；在 Adapter 中单独拉高页面则会让两端布局与 Core 产物不一致。直接修改 V0.1 Pattern 会改变历史页面。新规则须由版本锁选择，不能隐式迁移旧输入。

## 决策与实施边界

V0.2 静态页面采用 `height=max(1080, contentHeight)`：短页填满 1080，长页自然增高，不创建滚动、固定栏或交互状态。新增 V0.2.2 Token `size.page-min-height=1080` 与独立 Pattern 选择；仅明确选择该版本时，Page 带最小高度约束。Layout Engine 仅对 Hug Page 应用该最小值，其他容器和 V0.1 保持原规则。以短页、长页、旧版回归和双端预检验收；完整原型流水线及原生新页面另行验证。
