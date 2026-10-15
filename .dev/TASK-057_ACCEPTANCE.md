# TASK-057 — 固定内容 Tag 的 V0.2.4 Registry 准入

日期：2026-10-15。状态：PASS（限定范围）；V0.2 整体发布仍 `NOT_READY`。

依赖 TASK-054 官方 View UI Plus 1.3.24 来源、TASK-055 原生候选、TASK-056 双端 Fidelity Gate PASS，以及用户批准的“新增内容范围约束后准入”。新增独立 `registries/components/v0.2.4` 快照，仅添加 `data.tag.default.enabled`：默认静态 variant、固定文字“启用”、默认尺寸/颜色、不可关闭、不可勾选、已选中、42×22。旧 V0.1 至 V0.2.3 快照及现有 V0.2 流水线输入包保持原锁，不自动迁移。

新快照完整嵌入 TASK-056 保真报告，锁定官方 Component IR 摘要、报告摘要、双端文件与组件 ID。Figma 绑定为 `0vGWSRoLxBiVPXiZ8xJAX9 / 176:16`；Penpot 绑定为 `57949053-620f-8001-8008-c804c8d61529 / f1153c87-a7fc-80d8-8008-c9a7f34bb9d8`。两端 CLI 可显式选择 `--component-library-version 0.2.4`，默认仍为 V0.1；V0.2 生产 profile 不静默切换到新快照。

Core 的固定文字规范化要求来源证据绑定的 label 恰为“启用”，随后仅引用原生组件而不覆盖文字；Adapter 写入前拒绝文字、槽、样式和尺寸覆盖。Schema、Registry 与双端绑定均验证固定范围，错误文案、错误尺寸、错误原生 ID 及篡改保真报告会失败。

验收：Tag 准入、Tag Gate、Table 回归 12 项定向测试通过；架构检查与 Git diff 检查通过。`admission.json` 记录 `registryAdmission=PASS` 和 `releaseReady=false`；TASK-056 原始 Gate 仍保留 `NOT_RUN` 准入状态。尚未用新独立原型进行 V0.2.4 完整页面验收，中文实际回退字体身份仍为 `UNVERIFIED`。
