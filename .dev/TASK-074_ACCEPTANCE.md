# TASK-074 — Pagination Figma 默认字体原生候选

日期：2026-10-15。状态：**CANDIDATE_REVIEW**；单端独立 QA、双端 Fidelity Gate 与 Registry 准入尚未执行。Penpot 线按用户决定暂缓。

依赖 TASK-073 官方三页静态来源。Figma 目标文件新建 `V0.2 / Default-font Pagination candidate` 页，400×32px 原生主组件 `205:16` 与真实实例 `205:29`；五个 32×32px 原生控件在 x=0、36、72、108、144，固定第 1 页选中，数字 1、2、3 使用 Inter Regular 14。白底、默认边框 `#DCDEE2`、选中蓝边 `#2D8CF0`、文字色 `#515A6E` 均与来源一致并绑定变量。

功能箭头采用仓库已同步且哈希锁定的 Remix Icon 4.9.1 `arrow-left-s-line.svg` 和 `arrow-right-s-line.svg`，在 Figma 中作为各自原生主组件与真实实例；通过 SVG `viewBox` 缩放到 20px，未手绘图标。原始 SVG 哈希为 `7d0407d47b59e7d69446ef81b79e95c5d5a4085e7fa7ba30770556b67197407e` 与 `2c579a4dbaf25e19a128d71e04f4cf43b19ad2487a0076ff7e7e5a94c9b3e013`。官方 View UI Plus 样张使用自身图标字体，图标改编差异须在正式 QA 中单独评估。

[候选审计](../artifacts/task-074/pagination-candidate-audit.json)9 项检查通过；Figma 独立读回、PNG/SVG 和重复 PNG 见 [证据目录](../artifacts/task-074/figma)，重复 PNG 逐字节相同。候选元数据在 `adapters/figma/metadata/pagination-default-font-candidate-0.2.0.json`。测试：`python -m unittest tests.test_default_font_pagination_candidate_v02`，2 项 PASS。

当前 `admissionEligible=false`、`registryAdmission=DEFERRED_PENPOT`、`releaseReady=false`，不得登记正式 Registry。
