# TASK-080 — Tree Figma 默认字体原生候选

日期：2026-10-19。状态：**CANDIDATE_REVIEW**；正式单端 QA、双端 Fidelity Gate 与 Registry 准入尚未执行。Penpot 线按用户决定暂缓。

依赖 TASK-079 官方固定展开三节点来源。Figma 目标文件 `V0.2 / Default-font Tree candidate` 页建立 240×79px 原生主组件 `210:6` 和真实关联实例 `210:15`。三行分别位于 y=0/29/58，高 21px；可编辑文字“部门”“研发部”“设计部”为 Inter Regular 14/21。父节点箭头使用已同步并哈希锁定的 Remix `arrow-right-s-line` 原生主组件 `210:5` 和关联实例 `210:13`，旋转为展开向下状态。正文 `#515A6E` 绑定既有来源变量。

[候选审计](../artifacts/task-080/tree-candidate-audit.json)9 项检查 PASS。Figma 独立读回、PNG/SVG、重复 PNG 存于 [证据目录](../artifacts/task-080/figma)，两次 PNG 逐字节一致。候选元数据在 `adapters/figma/metadata/tree-default-font-candidate-0.2.0.json`。测试：`python -m unittest tests.test_default_font_tree_candidate_v02`，2 项 PASS。

当前 `admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`，不得登记正式 Registry。
