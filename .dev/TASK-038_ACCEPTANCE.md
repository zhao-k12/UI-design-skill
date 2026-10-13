# TASK-038 — 固定内容 Select 的 V0.2.2 Registry 准入

日期：2026-10-13。状态：PASS（限定范围）。沿用用户对 V0.2 “新增内容范围约束后准入”的决策，不扩展到任意 Select 文案或状态。

独立的 `registries/components/v0.2.2` 快照保留 V0.2.1 已验收的“查询” Button 与固定占位 Input，新增 `form.select.default.medium`。Select 只允许 `default` 静态 variant、官方 `modelValue=enabled`、所选文字“启用”和 240×32。Schema 明确表达此固定范围；V0.1、V0.2.0、V0.2.1 及旧绑定均不迁移。

TASK-037 的双平台 Select 保真报告完整嵌入新快照，并以 Component IR SHA、报告摘要、原生组件 ID、目标文件 ID 与两端 Adapter Fidelity Metadata 校验。Figma 绑定指向 `152:10`；Penpot 绑定指向新验收文件中的 `4b3abcb2-3ae8-803f-8008-c8485c8b9729`。`admission.json` 另行记录 `registryAdmission=PASS`，TASK-037 原始报告保留验收时的 `NOT_RUN`。

Core Assembly 先根据来源证据核验显示文字 `value=启用`，再只引用已有原生组件，不注入文字覆盖。其他文字、空值、额外槽、样式或尺寸变化会失败。Figma/Penpot Adapter 在写入前重复检查。两端 CLI 可以显式选择 `--component-library-version 0.2.2`，默认仍为 V0.1。

注册、Core 组装及两端 Adapter 的 26 项定向与回归测试通过。完整旧版套件执行 534 项，出现 29 个错误与 1 个失败：主要涉及本机缺失的历史 Arial/PingFang 文件、FreeType 运行库、早期忽略的验收产物及 Brotli 扩展；锁定旧程序哈希的发布测试也因本次程序更新而与历史快照不匹配。这些不作为 V0.2.2 发布通过的证据，需在发布流程中单独处理。页面实际排版与视觉交付尚未验收，`releaseReady=false`；中文实际回退字体身份仍为 `UNVERIFIED`。下一步是 Table 的默认字体来源审计与保真验收。
