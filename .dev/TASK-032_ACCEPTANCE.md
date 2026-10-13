# TASK-032 — 固定内容 Button 的 V0.2 Registry 准入

日期：2026-10-13。状态：PASS（限定范围）。架构冲突及用户决策见 [TASK-032_ARCHITECTURE_CONFLICT.md](TASK-032_ARCHITECTURE_CONFLICT.md)。

## 准入结果

- 新快照 `registries/components/v0.2.0/{catalog,fidelity-reports}.json` 只将 `action.button.primary.medium` 的 `default` variant 登记为 active，内容范围锁定原生文字“查询”、60×32、无内容和样式覆盖。其报告是 TASK-031 双平台默认字体保真门 `0.2.2` 的完整快照。旧 V0.1 schema、Registry、Fidelity 报告和绑定均保留。
- `adapters/{figma,penpot}/metadata/component-bindings-0.2.0.json` 分别绑定 Figma `135:15`、新 Penpot 文件中的 `4b3abcb2-3ae8-803f-8008-c805b99e5b4e`。绑定构造时与报告内的目标文件和原生组件 ID 逐项比对；生成脚本还核验 TASK-031 原始报告及候选 Metadata 的 SHA256。
- 独立的 `registries/components/v0.2.0/admission.json` 记录 `registryAdmission=PASS` 和 `scopedPageGenerationReady=true`。TASK-031 的原生 Fidelity Gate 报告保持验收时的 `registryAdmission=NOT_RUN`，不回写历史证据。
- Core Assembly 先通过来源引用验证 label 恰为“查询”，然后使用主组件内的固定文字，不再向设计工具注入 label。来源内其他文字、额外 Props/Slots 与超出 60×32 的实例会返回失败。Figma/Penpot Adapter 在写入脚本生成前再次校验范围；Penpot 仅对本版本双平台门使用其原生证据，V0.1 仍走原有独立 receipt。
- 两端 CLI 增加显式 `--component-library-version 0.2.0`，默认继续读取 V0.1。未准入的 Input/Select/Table 不进入 V0.2 快照。

## 验证与边界

- `scripts/default_font_button_gate_v02.py` 复核 PASS；`scripts/admit_default_font_button_v02.py` 构建快照和两端绑定 PASS。
- 新增测试覆盖范围扩张、报告篡改、原生绑定重定向、组装内容正规化与两端真实 Adapter 预检。Core 检查和相关历史 Assembly/Placement/Registry 套件通过。
- 这是固定内容样张的准入，不代表任意 Button 文案、状态或尺寸已验收。`effectiveCjkFontIdentity` 仍为 `UNVERIFIED`；页面视觉交付与发布验收尚未执行。
