# TASK-068 — Switch 双平台默认字体原生候选

日期：2026-10-15。状态：CANDIDATE_REVIEW；正式 Fidelity Gate 与 Registry 准入均 `NOT_RUN`。

依赖 TASK-067 已锁定的 View UI Plus 1.3.24 选中态 Switch 来源。Figma 目标文件新建 `V0.2 / Default-font Switch candidate` 页，创建 44×22px 原生主组件及关联实例，固定文字“开”使用 Inter Regular 12。Penpot 当前验收文件同名页创建原生主组件及关联实例，文字使用 sourcesanspro regular 12；文件校验无错误。蓝色背景沿用已锁定来源色 `#2D8CF0`，白色 18×18px 滑块和文字均为原生可编辑图层，滑块位置 x=24、y=2。

[候选审计](../artifacts/task-068/candidate-audit.json)的双端各 7 项检查均通过。Figma 与 Penpot 独立读回、PNG/SVG 和重复 PNG 保存在 [候选证据](../artifacts/task-068)；各端重复 PNG 逐字节相同。与官方 44×23px 元素截图比较时先确认额外底行全白；初步诊断的文字外最大 RGB 通道差 Figma 27、Penpot 71。Penpot 差异集中在胶囊边缘与滑块圆边的抗锯齿，正式 Gate 还须限定区域、核对实色区及字形完整性。

候选元数据分别位于 Figma/Penpot Adapter `switch-default-font-candidate-0.2.0.json`，均标记 `CANDIDATE_REVIEW`、`nativeAdmission=NOT_RUN`。当前证据不允许准入 Registry 或宣称 V0.2 发布就绪。
