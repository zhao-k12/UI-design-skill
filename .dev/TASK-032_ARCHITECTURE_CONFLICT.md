# TASK-032 — ARCHITECTURE_CONFLICT: 字体改编 Button 的内容范围与 Registry

日期：2026-10-13。状态：RESOLVED。用户选择“新增内容范围约束后准入”。依照 `CONSTRAINTS.md` 第 16 条，先记录冲突，再在独立 V0.2 契约中执行内容和尺寸约束；V0.1 历史快照不迁移。

## 当前设计

V0.1 `ComponentRegistry` 以逻辑 ID、variant、slots 和 Fidelity 报告判断 active；`resolve(logical_id, variant)` 不接收实际文本、Props 或内容上下文。Button 的既有逻辑 ID `action.button.primary.medium` 可以由页面组装器填入任意来源文字。`ComponentBindings` 只检查版本与原生组件引用，不约束内容。

## 实际冲突与影响

TASK-031 新保真门只验证 View UI Plus 1.3.24 的 60×32 primary/default Button，文字“查询”，Figma Inter Regular 与 Penpot sourcesanspro regular 的双平台原生输出。新字体的文字宽度、字形及整体几何不能自动推广到其他文字、状态或尺寸。若沿用原有 Registry 结构将同一逻辑 ID 直接标为 active，组装器可能生成没有测量或保真证据的 Button；这违反 `CONSTRAINTS.md` 第 4、5、11 条及已批准的 V0.2 改编政策。只增加 Fidelity PASS 哈希不能防止该范围外使用。

## 建议决策

推荐在**新版本** Registry 契约中加入可执行的准入内容范围（此例精确文字“查询”、尺寸和配置），并在 Component Mapping/Assembly 与 Adapter 写入前校验；范围外返回 `unsupported_component`，待另行测量。旧 V0.1 schema、Registry、报告和实例绑定不迁移。新 Registry 准入必须同时绑定 TASK-031 报告、两端原生组件 ID 和证据哈希。另一方案是暂缓 Registry active，仅保留 TASK-031 的 `admissionEligible=true`，直至通用内容契约确定。

实施边界：V0.2 的 Button 只准入固定原生文字“查询”、60×32、default variant、无额外 Props／Slot 或样式覆盖。页面组装必须先用来源证据验证 label，再引用原生固定内容。Figma/Penpot 写入前再次拒绝尺寸和内容覆盖。其他文字、状态、尺寸仍需独立测量与验收。
