# TASK-042 — ARCHITECTURE_CONFLICT: 页面自由文本与双平台默认字体

日期：2026-10-13。状态：RESOLVED FOR VERSIONED PREFLIGHT。用户已指定新设计使用 Figma/Penpot 各自默认字体，政策见 `docs/FONT_POLICY.md`。

## 当前设计

V0.1 `typography.heading/body` 在平台无关 Token 中写入 `Noto Sans SC`。两个 Adapter 按 `fontFamily:fontWeight` 查找原生字体绑定，并要求绑定 family 与 Token 完全相同。旧页面的自由 Text 因此无法在 Figma 映射到 Inter、在 Penpot 映射到 `sourcesanspro`，即使 V0.2.3 的四个固定原生组件已经分别验收默认字体。

## 冲突与影响

直接把 Core Token 改成 Inter 会把 Figma 的原生字体写入平台无关 Core，且在 Penpot 变为错误字体。继续使用旧 Token 会违反用户字体选择。若无目标文件绑定校验，仅用静态字典替换又会把一个文件的默认字体误用于其他文件。旧 Token 快照和历史任务不能被迁移。

## 决策与实施边界

新 V0.2 Token 快照使用语义字体族 `platform-default`；Core 只携带语义角色、字号、字重与行高。Adapter 按目标文件的已观测默认字体元数据解析真实 family/style/id，并锁定文件 ID 和观察记录哈希。未观测的字重须阻断预检。旧 V0.1 Token 和原有显式字体绑定行为不变。此任务只建立新字体预检契约，不宣称页面原生文字已完成验收。
