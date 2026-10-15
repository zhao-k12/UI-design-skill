# TASK-077 — Tabs Figma 默认字体原生候选

日期：2026-10-15。状态：**CANDIDATE_REVIEW**；正式单端 QA、双端 Fidelity Gate 与 Registry 准入尚未执行。Penpot 线按用户决定暂缓。

依赖 TASK-076 官方固定双标签来源。Figma 目标文件新建 `V0.2 / Default-font Tabs candidate` 页，320×73px 原生主组件 `207:3` 和真实关联实例 `207:14`。标签“概览”“详情”和选中内容“概览内容”均为 Inter Regular 14/21 可编辑文字。标签栏 320×36px；两标签各 60×37px，x=0/76；灰色底线 y=35、蓝色选中线 x=0/y=34、60×2px；内容从 y=52 开始。蓝色 `#2D8CF0`、灰线 `#DCDEE2`、正文 `#515A6E` 绑定既有来源变量。未选中“详情内容”不显示，符合官方运行样张。

[候选审计](../artifacts/task-077/tabs-candidate-audit.json)9 项检查 PASS。Figma 独立读回、PNG/SVG、重复 PNG 存于 [证据目录](../artifacts/task-077/figma)，两次 PNG 逐字节一致。候选元数据在 `adapters/figma/metadata/tabs-default-font-candidate-0.2.0.json`。测试：`python -m unittest tests.test_default_font_tabs_candidate_v02`，2 项 PASS。

当前 `admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`，不得登记正式 Registry。
