# TASK-035 — 固定占位 Input 的 V0.2.1 Registry 准入

日期：2026-10-13。状态：PASS（限定范围）。沿用用户对 V0.2 “新增内容范围约束后准入”的决策，不扩展到任意 Input 文案或输入状态。

## 结果

- 独立的 `registries/components/v0.2.1` 快照保留 V0.2.0 已验收的“查询” Button，并新增 `form.input.default.medium`。Input 只允许 `default` 静态 variant、空值、固定占位“请输入姓名”和 240×32。新 schema 同时表达两类固定原生内容；V0.1、V0.2.0 快照和旧绑定未迁移。
- TASK-034 双平台 Input 原生保真报告完整嵌入新快照，并以 Component IR SHA、报告摘要、原生组件 ID、目标文件 ID 与两端 Adapter Fidelity Metadata 校验。新 Figma 绑定指向 `141:3`，Penpot 绑定指向新文件中的 `4b3abcb2-3ae8-803f-8008-c811d08712ea`。`admission.json` 另行记录 `registryAdmission=PASS`；TASK-034 原始报告保留验收时的 `NOT_RUN`。
- Core Assembly 先以来源证据核验 `placeholder=请输入姓名`，再引用原生组件已有的固定占位，不注入设计覆盖。其他文字、非空值、额外槽和尺寸变化会失败。Figma/Penpot Adapter 在生成写入脚本前重复检查，Penpot 仅对本版已核验双平台报告免去 V0.1 receipt 路径。
- 两端 CLI 显式选择 `--component-library-version 0.2.1`；默认仍为 V0.1。新快照仅有两个已验收的固定内容组件，不包含尚未重测的 Select/Table。

## 检查与边界

`scripts/admit_default_font_input_v02.py` 构建新快照及绑定通过。测试覆盖范围扩张、原生引用重定向、来源内容正规化与两端 Adapter 正反预检；Core 及相关历史套件通过。页面实际排版和视觉交付尚未验收，`releaseReady=false`。中文实际回退字体身份仍为 `UNVERIFIED`。
