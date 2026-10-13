# TASK-041 — 固定内容 Table 的 V0.2.3 Registry 准入

日期：2026-10-13。状态：PASS（限定范围）。沿用用户对 V0.2 “新增内容范围约束后准入”的决策，冲突和实施边界见 [TASK-041_ARCHITECTURE_CONFLICT.md](TASK-041_ARCHITECTURE_CONFLICT.md)。

独立的 `registries/components/v0.2.3` 快照保留 V0.2.2 已验收的 Button、Input、Select，新增 `data.table.default`。Table 只允许 `default` 静态 variant、无表头/外边框/条纹、精确三列三行内容和 1392×144；Schema 与 Registry 均表达并核验此范围。V0.1 至 V0.2.2 快照及旧绑定没有迁移。

TASK-040 双平台保真报告完整嵌入新快照，并以 Component IR SHA、报告摘要、原生组件 ID、目标文件 ID 和两端 Fidelity Metadata 校验。Figma 绑定指向 `157:3`；Penpot 绑定指向替代验收文件中的 `4b3abcb2-3ae8-803f-8008-c85957bd3a28`。`admission.json` 独立记录 `registryAdmission=PASS`；TASK-040 原始保真报告保留验收时的 `NOT_RUN`。

Core Assembly 逐格核验 `tableRecords` 来源 claim 与固定九格数据，并要求已绑定的 Component IR 的列、数据和 1392×144 几何相符；通过后只输出无内容覆盖的原生组件实例。缺少记录、不同数据、伪造来源引用会失败。Figma/Penpot Adapter 在写入前重复拒绝内容、样式和尺寸覆盖。两端 CLI 可显式选择 `--component-library-version 0.2.3`，默认仍为 V0.1。

Table 注册、Assembly 来源记录及两端 Adapter 的定向测试通过。页面实际排版与视觉交付尚未验收，`releaseReady=false`；中文实际回退字体身份仍为 `UNVERIFIED`。后续进入 V0.2 页面能力开发。
