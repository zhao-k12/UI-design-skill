# TASK-025 — ARCHITECTURE_CONFLICT: 默认字体与官方组件字体保真

日期：2026-10-13。状态：OPEN；影响 V0.2 新字体组件的测量与原生准入，不影响 V0.1 历史任务。

## 当前设计

CONSTRAINTS.md 要求官方组件视觉真值来自官方源码、CSS 和真实浏览器运行，并且 Fidelity Gate 通过后才能进入 Registry。V0.1 既有组件使用 View UI Plus 1.3.24 官方 CSS 字体栈；对应的浏览器/原生证据及版本锁已经冻结。用户明确指定 V0.2 新设计使用 Figma/Penpot 各自原生默认字体；TASK-024 已在实际目标文件观测到 Figma Inter、Penpot sourcesanspro。

## 实际冲突和影响

TASK-025 审计读取锁定官方 Component IR：Button、Input、Select 每类有一组可见文字样式，Table 有两组。全部官方 CSS 声明的字体栈都没有 Inter 或 sourcesanspro。完整输入文件和目标绑定 SHA256、逐组件的 CSS 声明、文字路径及样本文字在 artifacts/task-025/source-font-compatibility.json。

旧尺寸和截图测量由原字体环境生成；将其直接赋给新默认字体组件，或者沿用旧 Fidelity PASS，会同时破坏字体选择和证据约束。仅修改 Token、Adapter font binding 或 Registry 声明也不能提供真实新组件测量。`font-family` 属性只是 CSS 声明，不证明浏览器对每个中文字形最终使用了哪份字体文件；TASK-024 也没有证明有效 CJK fallback 身份。

## 建议的 V0.2 决策

明确将平台默认字体视为**版本化设计改编**：官方源码仍约束组件结构、Props、非文字几何和视觉样式；新版本按平台默认字体独立测量文字和组件整体，分别进行原生截图、实际属性、字形完整性及保真审查。新的参考/例外规则必须规定哪些非文字参数严格一致、文字尺寸变化如何记录、何种 native 与来源比较可准入，并通过反例测试。不能把官方旧截图改名为“默认字体参考”，也不能以当前样张宽高替代组件测量。

另一个可行选择是维持 V0.1 原字体严格保真；这与用户要求的新设计使用平台默认字体不一致，因此只可用于历史复验。

**依赖门**：在 V0.2 改编与 Fidelity 规则获明确架构决策前，继续保留 Button/Input/Select/Table 的 `measurement=NOT_RUN`、`nativeAdmission=NOT_RUN`，不得生成正式准入组件。独立的来源审计、环境准备、Core 与文档工作可继续。
