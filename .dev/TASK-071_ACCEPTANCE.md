# TASK-071 — Card Figma 默认字体原生候选

日期：2026-10-15。状态：**CANDIDATE_REVIEW**；正式单端 QA、双端 Fidelity Gate 与 Registry 准入均未执行。Penpot 线按用户决定暂缓。

依赖 TASK-070 锁定的 View UI Plus 1.3.24 官方 Card 来源。Figma 目标文件创建 `V0.2 / Default-font Card candidate` 页，240×106px 原生主组件 `198:8` 与真实关联实例 `198:14`。标题“用户信息”使用 Inter Medium 16/22；正文“暂无内容”使用 Inter Regular 14/21。保留官方白底、`#E8EAEC` 边框和分隔线、`#17233D` 标题色、`#515A6E` 正文色，全部颜色绑定当前文件的来源变量。标题区 238×51px、内容区 238×53px，分别从边框内侧 x=1 起。

[候选审计](../artifacts/task-071/card-candidate-audit.json)8 项检查通过；Figma 独立结构读回、PNG/SVG 和重复 PNG 保存于 [证据目录](../artifacts/task-071/figma)。重复 PNG 逐字节一致，截图人工确认标题、分隔线及正文完整。候选元数据记录于 `adapters/figma/metadata/card-default-font-candidate-0.2.0.json`。测试：`python -m unittest tests.test_default_font_card_candidate_v02`，2 项 PASS。

当前仅是 Figma 候选：`admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`。下一步单端独立 QA；不得将候选登记为正式组件。
