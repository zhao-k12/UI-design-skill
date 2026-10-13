# TASK-026 — 平台默认字体改编决策与输入锁

日期：2026-10-13。用户明确选择“采用新版本字体改编与重新验收”。该决定解决 TASK-025 记录的 V0.2 字体与旧官方字体栈冲突；V0.1 原有来源、Registry 和 Fidelity 结果不变。

## 实施

- `policies/font-adaptation-0.2.0.json` 锁定官方组件结构、Props 与非文字视觉来源；Figma Inter 和 Penpot sourcesanspro 分别测量文字与组件整体，分别进行独立原生捕获、字形完整性和保真检查。旧字体尺寸、截图、组件 ID 和准入 PASS 均不能继承。
- `scripts/font_adaptation_manifest.py` 核对用户决策、TASK-025 来源 SHA256、两端目标绑定 SHA256、TASK-024 profile PASS 和四类组件覆盖；旧数据变化或虚假准入会使输出失效并失败。产物 `artifacts/task-026/font-adaptation-manifest.json` 状态为 `INPUTS_LOCKED_MEASUREMENT_PENDING`，每组件 measurement/nativeAdmission 仍为 NOT_RUN。
- 新增 5 项清单测试；core 分组 156 项 PASS，日志在 `artifacts/task-026/core`。

## 后续

下一步按此输入锁分别构建和测量 Button/Input/Select/Table 的 V0.2 原生候选，再定义逐字段新 Fidelity Gate、独立导出与新版本准入。当前清单仅可启动测量，不允许生成正式页面或宣称组件准入。
