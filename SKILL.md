---
name: ui-design-skill
description: Understand a UI prototype, normalize its layout against iView and project rules, and generate staged, audited HTML or editable Figma pages through a retained color skeleton, default-copy page, content fill and final proofread. Penpot is deferred.
---

# UI Design Skill

读取 [开发状态](.dev/DEVELOPMENT_STATE.md)、[架构](ARCHITECTURE.md) 和 [约束](CONSTRAINTS.md)。V0.1 的具体验收范围及命令见 [流水线使用说明](core/pipeline/README.md)。AI 负责理解和选择，程序负责布局与执行，官方组件负责视觉真值。公开环境与证据边界见 [发布说明](docs/PUBLICATION.md)。

## 主流程：原型 → 页面

用户指定 HTML 交付时，优先使用 [HTML 执行说明](docs/HTML_WORKFLOW.md)：以官方 View UI Plus 运行包/CSS 输出自包含 `skeleton.html`、`default.html`、`final.html`，逐阶段浏览器截图和 QA。复用同一内容 Tree、布局决策与 iView 规范门；不为 HTML 交付等待 Figma 原生写入。用户指定 Figma 原生可编辑交付时继续下述 Figma 阶段。HTML→Figma 导入是后续独立验收，不把 HTML 页面当成已完成的 Figma 原生实例。HTML 首版仍受当前 Core 固定内容范围约束，不能宣称任意新文案已可生成；版本化迁移决定见 [TASK-128](.dev/TASK-128_HTML_DELIVERY_DECISION.md)。

当前新任务使用 [分阶段主流程](docs/WORKFLOW_V03.md)。Figma 原生路线与 HTML 路线都遵循相同阶段顺序；Penpot 全线按用户决定搁置。下文的原生页面要求适用于 Figma 路线，HTML 路线的浏览器 QA 细节见 [HTML 执行说明](docs/HTML_WORKFLOW.md)。

在解析原型前锁定本任务的设计规范来源。当前组件视觉来源是官方 View UI Plus 1.3.24；页面留白等官方未指定的行为使用显式的项目布局规则。原型提供内容、层级、顺序和明确的业务关系；原型的留白、控件尺寸、贴边或残缺画法默认不是最终几何依据。Figma 默认字体是用户已批准的专项改编。

模型在语义 Tree 审核后、Core 布局运行前完成**规范化布局决策**，这是 Tree → 骨架之间的内部工作，不增加用户可见的主步骤。逐项分清来源事实、规范要求、项目规则和设计推断；从这些依据决定容器、24 栅格、内边距、对齐与占宽，并写入来源绑定的布局意图和布局计划。可补充展示所需的容器、背景和留白，不得补造业务字段、操作或数据。不得从旧示例复制布局计划再只更新哈希，也不得以“忠实原型”为由保留无依据的空白或零内边距。适用的列表页规则和决策契约见 [布局决策与质量门](docs/WORKFLOW_V03.md#规范化布局决策)。

Core 仍只按固定规则执行几何。新任务使用组件库 V0.2.9：组件的来源测量宽高是样本证据，不是准入条件；布局计划可声明本次画布宽度。列表 Table 使用经原生验证的自适应主组件填满内容区，普通控件按自身内容取固有尺寸并在 Cell 内对齐。检查溢出、原生结构和内容来源，不因 Cell 与历史样本宽度不同而要求新增组件。其它页面模式没有已批准的项目规则时标为 Review，不套用列表页数值。

**生成前一次性排除已知失败**：新 Figma 任务先用 `v0.2.9-figma` 运行资源预检，再运行 Core。预检同时核对官方来源锁、iView 色彩 Token、当前原型的结构与布局可计算性、组件映射与 Figma 绑定，并对 Table 核对实际 Cell 可容纳高度、原生表头、非尺寸来源配置和固定数据范围；Table 宽度由布局决定。`readiness_preflight.json` 必须为 `READY`；`NEEDS_RESOURCE` 或 `REVISE_INPUT` 时按具体 issue 修正来源、组件或输入，不能继续创建原生页。预检通过后仍须执行完整 Core、规范门和原生 QA。准备骨架脚本时先预编译默认组件页，两个页面的脚本都能生成后才写入 Figma。生成脚本只含 ASCII 转义字符，避免 Windows 终端传递中文时损坏标签。命令与产物见 [分阶段主流程](docs/WORKFLOW_V03.md#生成前预检)。

1. **统一页面内容 Tree**：阅读原型，保存有原文、位置与来源证据的 observations。把页面内容、层级和布局关系合成一棵 Tree，不再把旧 Page Tree 与 Layout Tree 当成两个对用户交付的步骤。Tree QA 核对原型内容正确、完整；遗漏源图内容须人工复核，不把来源观察自身当作完整性证明。原型或审核指纹变化后重新检查。
   在建立原生骨架前，独立运行布局质量门与 iView／View UI Plus 组件规范门。布局门要把模型的布局意图与实际 Core 几何、项目规则及正式组件尺寸逐项比较；只有原生页面忠实于**合格**布局计划才有意义。iView 门核对官方来源锁、页面 Token 和组件组合；源原型要求表头时必须使用已准入的原生带表头 Table，不能在 `showHeader=false` 的表格上另拼 Frame/Text。任一门 FAIL/Review 时暂缓其依赖的原生动作，进入下述诊断与修复循环；平台默认字体改编继续有效。当前两门只覆盖明确列出的规则，不代表 iView 全量规范已验证。
2. **保留彩色组件骨架页**：按已通过布局质量门的 Tree、布局意图和确定性规则计算每个 Cell，标明选用组件、类型和不同颜色。在设计文件中新建并保留独立骨架页面。骨架 QA 核对组件选择、内容放置完整、位置、栅格与间距，尤其核对区域内边距、内容边界和填充策略；必须独立读取原生页面，旧 HTML 标注不代替页面。
3. **新建默认文案组件页**：仅在骨架 QA 通过后，按该骨架新建另一页面，放入正式 Registry 准入的真实组件实例，组件保留官方主组件默认内容；骨架页不被覆盖。独立读回组件引用、默认文字和结构。骨架修订时生成新 revision 的组件页，不能静默覆盖旧版。
4. **填入原型内容**：仅在默认文案组件页 QA 通过后，在该组件页填入来源绑定的原型文字。逐项读回，检查填写正确、无疏漏。固定内容范围外的组件文字不得私自改写；先扩展准入或报告 Unsupported。
5. **最终原型校对**：把完成页面的内容和原型逐项对照；把页面几何与布局意图及规范逐项对照，并审核完整原生 PNG、文字、组件、栅格、间距、占宽及溢出。Tree、布局质量、iView 组件规范、骨架、默认组件页、填入内容及最终校对全部 PASS，才允许交付；内容正确不能代替设计规范通过。

**FAIL/Review 恢复循环**：质量门失败是待处理工作，不是整项任务结束。读取具体 issue 与来源证据，分辨原型理解错误、布局计划错误、Token 不符、正式组件能力缺口、原生执行错误或校对遗漏；修正最早受影响的输入或资源，在新的版本／revision 重跑该阶段及依赖阶段，直到全部 PASS。组件缺口要从锁定官方源码重新提取所需配置、完成当前平台原生保真和 Registry／绑定准入；不得用旧页面、未准入候选或虚构 PASS 代替。可持续处理的失败继续推进，并向用户说明进展；只有 skill 的契约／实现本身阻止了合法修复，或客观依赖无法取得且无法在现有约束内解决时，才记录明确阻塞原因与已尝试修复。不得因一次 QA FAIL 直接宣布任务完成。

旧 `scripts/run_pipeline.py` 与既有任务目录保留历史版本语义；新任务使用 `scripts/prepare_revised_workflow.py` 和 `scripts/run_revised_figma_stages.py` 的分阶段门。阶段准备结果不等于原生 QA 或可交付结论。

只使用正式准入 Registry 和锁定的 Token／Remix 版本。静态文字与布局原语可按显式契约组合；不得用它们模拟缺失官方控件。缺失记录 Missing，不确定记录 Review，不支持记录 Unsupported；不得偷偷替换原型内容、图片、字体、图标或组件。组件按版本化尺寸策略放置：`intrinsic` 保持内容固有尺寸，`fill-cell` 使用经验证可自适应的原生主组件；不能仅缩放外框、遮盖内部溢出。当前原生 Image 未准入。

Core 不接触平台 API 或节点 ID，平台引用只留在 Adapter Metadata 和实际证据中。不得绕过 UI-IR、Validator 或原生保真门。当前正式组件及示例目标文件已列在流水线说明；其他文件的真实引用须重新预检，不能照搬示例 ID。

每个任务锁定版本并保存 checkpoint；输入或映射变化从受影响阶段恢复，组装保留 Cell ID／box，只声明受影响 Section。版本／程序迁移使用新任务目录，不能自动升级已有锁。原生导出失败保存 PARTIAL，只有同 revision、同实际节点状态允许复用成功格式。实际截图仍须原生 PNG。

已批准的 AD-017 允许有完整几何、样式、字体、轮廓、基线、独立向量及边缘证据的栅格差异；两份 Remix 图标另使用已批准的精确 Float32 路径规则。适用范围以 [.dev/TASK-009_FIDELITY_DECISION.md](.dev/TASK-009_FIDELITY_DECISION.md) 和 TASK-010 决策文件为准。不能引入宽泛容差、覆盖历史失败或把批准本身当作验收。

## 继续开发

V0.2 正在按限定范围开发，已完成的部分和下一动作以 [开发状态](.dev/DEVELOPMENT_STATE.md) 及 [发布就绪审计](docs/V02_RELEASE_READINESS.md) 为准；完整目标见 [V0.2自主持续开发计划](docs/DEVELOPMENT_PLAN_V0.2.md)。用户明确授权开发后按阶段依赖推进，先核对复用已有能力。历史 [.dev/BUILD_PLAN.md](.dev/BUILD_PLAN.md) 是V0.1架构来源，不是新版本未完成队列。运行检查和实际验收，保存产物、状态和Commit后进入下一阶段。发现冻结架构冲突，记录当前设计、原因、影响和提案；在决策明确前停止依赖变更。能力变更重新说明范围并实际验证，不以临时Demo或模拟平台输出宣称完成。尊重暂停，不因读取计划而启动后台任务。
