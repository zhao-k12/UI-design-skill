# UI Design Skill

静态 B 端 UI 设计 Skill。由 Codex 理解原型，以内容Tree配置官方 View UI Plus 组件，经Core和UI-IR生成可离线打开、保留真实文字的静态HTML页面。

当前入口为 [SKILL.md](SKILL.md) 与 [HTML流程](docs/HTML_WORKFLOW.md)。新任务采用[通用内容组合](docs/HTML_COMPOSITION.md)，不按页面名称、列数、文案或尺寸选择专用生成器。官方组件通过属性、插槽和数据组合；仍需本次原型的内容和视觉复核，不能把通用渲染支持视为所有组合已验收。

## 当前 HTML 路线

- **按 Skill 完整执行**：启动、恢复及继续任务均适用；未通过验收继续修正，实际截图复核后才发布。人工没提出的内容不自行调整。
- **默认 Logo**：除非用户明确指定其他 Logo 或文字替代，否则始终使用仓库默认 Logo；原型中的品牌文字不构成替换授权。
- **来源预检**：初读与独立复扫分别记录来源特征、菜单实例及有序表头，并绑定完整 Tree。缺失证据阻止新任务渲染；程序不能证明观察真实。
- **通用装配**：复用侧栏、顶栏、面包屑、摘要、步骤条、模块、表单和表格能力；布局不依赖历史页面业务内容。
- **实际布局检查**：检查输入内容截断、标签换行、模块边距、关闭图标及已声明的布局关系；静态表格支持表头/正文共享横向滚动，并检查较小视口。
- **失败可恢复**：保存失败尝试及可用输入，保留已有发布文件；最新尝试未通过时，拒绝使用旧审核冒充本次完成。
- **发布可核验**：`render` → 实际截图复核 → `finalize` → `verify`。预览、机器 PASS 和文件哈希一致均不能替代视觉判断。

快速命令与证据格式见 [HTML 快速流程](docs/HTML_FAST_WORKFLOW.md)，模块范围见 [已确认模块](docs/CONFIRMED_REUSABLE_MODULES.md)，静态表格及机器计时边界见 [运行时验证补充](docs/RUNTIME_VALIDATION_NOTES.md)。常规页面以五分钟内交付为目标，不是已达成的性能保证；导出器机器耗时不等于完整任务耗时。

## 工作方式

```text
静态原型 → 内容Tree与布局关系 → Core / UI-IR → 官方HTML组件递归组合
→ 同一结构的彩色骨架 / 默认组件 / 原型内容 → 一次综合校对 → 静态page.html
```

AI 理解内容、选择规则和组件；程序计算布局与验证；官方源码、CSS 和真实运行结果提供视觉真值。Core 不依赖平台 SDK，实际平台引用保存在 Adapter Metadata。

## 历史原生链路能力与边界

下述V0.1/V0.2原生平台与Profile资料保留用于历史追溯，不作为当前HTML任务入口或固定结构限制。

| 能力 | 当前范围 |
|---|---|
| UI-IR、Schema、Manifest | 平台无关描述、显式版本锁、预检 |
| 原型与结构 | 来源绑定的语义观察、Page Tree和语义复核；当前没有自动OCR |
| 布局 | 24栅格、Stack、Fixed/Fill/Hug、确定性Skeleton和溢出检查 |
| 组件与图标 | 正式准入Registry、官方View UI Plus提取、Remix同步与语义查询 |
| 组装 | 组件映射、Cell槽位组合、受支持内容注入、完整性检查 |
| Figma / Penpot | 真实组件和图标关联实例、创建账本、独立读取及原生导出 |
| 恢复 | 阶段Checkpoint、输入指纹、依赖失效和Section局部重建 |
| 已验收案例 | 冻结用户管理列表、受支持槽位、有限冻结表格配置 |

首次列表验收为“姓名／状态／角色”三行，包含9项语义内容、4个UI实例和2个Remix图标。组件库 `0.2.1` 与 `0.3.0` 扩展有限的冻结表格配置，不表示任意数据、全部状态或全部Props均支持。详见[流水线说明](core/pipeline/README.md)、[组件库0.3.0](releases/component-library-0.3.0/README.md)和[历史验收](.dev/TASK-017_ACCEPTANCE.md)。

目前只生成静态设计，不生成业务代码、交互、动画或完整响应式页面。原生Image尚未准入。Missing、Review、Unsupported或失败质量门会阻止依赖阶段，不自动替换为近似控件。

## 如何使用 Skill

克隆仓库，在 Codex 项目对话中读取 [SKILL.md](SKILL.md)，提供静态原型，例如：

> 用 UI Design Skill 生成页面。读取本仓库 SKILL.md 并完整执行，按当前原型保留内容与状态，完成截图复核、finalize 和 verify 后交付。

Skill依赖仓库的程序、官方运行包和图标来源，不能只复制SKILL.md。当前HTML路线不需要Figma或Penpot连接。历史平台ID仅供追溯原验收，不授予访问权限。

GitHub 源码压缩包与安装后的磁盘占用不同：依赖、Chromium、运行产物及开发环境会另占空间。不要把整个开发目录当作安装包大小；当前未提供固定体积的独立精简安装包。

## 安装与检查

需要Python 3.11+、Node.js 24+和Git。在仓库根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm ci
npx playwright install chromium
node component-builder/runtime-renderer/extract.mjs --output artifacts/task-006
.\.venv\Scripts\python.exe validators/architecture.py
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests
node --test tests/*.test.mjs
```

只验证平台无关基础能力可运行 `.\.venv\Scripts\python.exe -m unittest tests.test_architecture tests.test_ui_ir tests.test_tokens tests.test_layout tests.test_layout_builder tests.test_component_registry`。完整字体/原生保真检查还需要指定字体、固定FreeType诊断环境和实际平台证据，这些资源不会自动安装。公开版省略账号界面截图，因此部分历史Manifest检查也需要本机原证据。缺少环境或证据不能视作PASS；详见[公开快照说明](docs/PUBLICATION.md)与[本次检查结果](docs/PUBLICATION_VALIDATION.md)。

## 历史 V0.2 原生开发记录

开发环境预检与分组测试入口已新增，见[开发检查说明](docs/DEVELOPMENT_CHECKS.md)。它们区分依赖缺失、证据变化和实际测试失败，不替代原生验收。

新证据包可以使用[可移植证据契约](docs/PORTABLE_EVIDENCE.md)打包和验证原始字节；完整性通过不表示原生准入。

官方运行环境支持[两次真实提取复验](docs/RUNTIME_REPLAY.md)。后续新设计字体使用 [Figma/Penpot 各自的默认字体](docs/FONT_POLICY.md)，实际绑定须在目标会话验证。

当前开发范围已按用户决定改为 **仅 Figma**，不再安排 Penpot 开发或验收。新的 `v0.2.7-figma` 生产 Profile 一次准入 18 类已锁定的固定配置和 Figma 主组件引用；它不表示任意文字、状态或尺寸均可用。经审核的用户管理紧凑查询原型已完成新版九阶段 Core、Figma 原生页面、独立读回、重复 PNG、视觉复核和 10 项单端发布门。页面实际使用其中四类，其余 14 类有各自的原生主组件证据。Figma 使用 Inter。历史双平台 V0.2 发布目标未变更为已发布状态；单端范围与批量准入见 [TASK-116](.dev/TASK-116_FIGMA_SCOPE.md)、[TASK-118](.dev/TASK-118_FIGMA_BATCH_ADMISSION.md)。

当前原型可只提供 Figma 文件运行生产预检，无需 Penpot 文件：

```powershell
.\.venv\Scripts\python.exe scripts/run_figma_pipeline.py examples/user-management-compact-search-v027-figma --output-dir artifacts/my-figma-run --figma-file <Figma文件ID> --profile v0.2.7-figma
```

该命令保存九阶段 Core、Figma 原生计划和字节锁；实际写入 Figma 与原生复验仍需执行已校验的计划。旧双平台命令只用于历史复验。

剩余 11 类 Figma 候选可一次完成来源与原生证据核验，逐类问题写入同一报告：

```powershell
.\.venv\Scripts\python.exe scripts/audit_figma_candidate_batch.py --output artifacts/figma-candidate-batch.json
```

当前批次 11/11 证据通过，并已按官方运行属性、可见文字和尺寸快照准入新的 18 类 Figma 固定配置 Registry。该报告本身只负责证据核验；正式准入结果见新版本的 `admission.json`。

完整目标见 [V0.2 自主持续开发计划](docs/DEVELOPMENT_PLAN_V0.2.md)：

- 提前建设18类组件，以及明确的变体、状态、尺寸和配置覆盖范围。
- 页面、Section、复杂表格模式和1920宽画布布局政策。
- 图片原型理解、带来源记录的设计默认值与模拟数据。
- 仅调用正式Registry的自动组装、规则驱动视觉修正。
- 用户选择目标平台；两平台能力分别通过发布验收。
- 阶段自动推进、测试、记录、提交、断点恢复和冲突处理。

当前定义的 Figma 固定配置范围已通过 10 项单端发布门；扩展到其他文案、状态或尺寸仍需新的来源与保真证据。旧版完整目标计划保留作历史背景。当前开发不意味着启动后台任务；未执行的检查不计为通过。

## 阅读入口

- [SKILL.md](SKILL.md)：Agent执行入口。
- [ARCHITECTURE.md](ARCHITECTURE.md)、[CONSTRAINTS.md](CONSTRAINTS.md)：已实现架构与冻结边界。
- [.dev/DEVELOPMENT_STATE.md](.dev/DEVELOPMENT_STATE.md)：公开版状态与后续方向。
- `core/`、`schemas/`、`validators/`：平台无关流水线与校验。
- `component-builder/`、`icon-manager/`、`registries/`：官方资产提取、同步与准入。
- `adapters/`、`examples/`、`tests/`、`releases/`：平台执行、输入、测试和版本快照。

第三方组件和图标遵循其上游许可证。仓库不含Arial、苹方等专有字体文件，不授予其使用或分发权。本项目尚未选择独立开源许可证；公开可见不等于授予开源许可。
