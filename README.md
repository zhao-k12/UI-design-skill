# UI Design Skill

平台无关的静态 B 端 UI 设计 Skill。由 Codex 理解静态原型，再通过确定性布局、官方组件库和 UI-IR，生成 Figma 或 Penpot 原生可编辑设计稿。

**已实现：V0.1 有限范围的设计流水线；V0.2 正在按限定范围开发。** 当前并非任意截图、任意组件的一键生成工具。

## 工作方式

```text
静态原型 → 语义分析 → Page Tree → 结构检查
→ 布局模式 → Layout Skeleton → 布局检查
→ 组件映射 → 正式组件组装 → 内容与资源注入
→ 规则检查 → UI-IR → 目标平台 Adapter → 原生验收
```

AI 理解内容、选择规则和组件；程序计算布局与验证；官方源码、CSS 和真实运行结果提供视觉真值。Core 不依赖平台 SDK，实际平台引用保存在 Adapter Metadata。

## 已有能力与边界

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

克隆仓库，在 Codex 项目对话中读取 [SKILL.md](SKILL.md)，提供静态原型。当前开发只走 Figma，例如：

> 读取 SKILL.md，分析我提供的静态原型，使用已准入组件生成 Figma 可编辑设计稿。先核对原型内容，保存分析、布局、UI-IR 和验收结果。

Skill依赖整个仓库的程序、Schema、Registry和证据，不能只复制SKILL.md。平台执行需要当前会话可用的连接器或公开插件SDK、目标文件权限和合法字体。历史平台ID仅供追溯原验收，不授予访问权限，也不能直接照搬到其他账号。

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

## 开发中的 V0.2

开发环境预检与分组测试入口已新增，见[开发检查说明](docs/DEVELOPMENT_CHECKS.md)。它们区分依赖缺失、证据变化和实际测试失败，不替代原生验收。

新证据包可以使用[可移植证据契约](docs/PORTABLE_EVIDENCE.md)打包和验证原始字节；完整性通过不表示原生准入。

官方运行环境支持[两次真实提取复验](docs/RUNTIME_REPLAY.md)。后续新设计字体使用 [Figma/Penpot 各自的默认字体](docs/FONT_POLICY.md)，实际绑定须在目标会话验证。

当前开发范围已按用户决定改为 **仅 Figma**，不再安排 Penpot 开发或验收。V0.2.6 生产 Profile 包含 Button、Input、Select、Table、Tag、Checkbox、Radio 各一项固定内容配置；七个 Figma 主组件引用已再次核验。经审核的新用户管理紧凑查询原型已通过 Figma 原生端到端验收和九项单端发布门，页面实际使用前四类。18 类目标组件均有 Figma 原生证据，其中 11 类仍只有候选 QA。Figma 使用 Inter。历史双平台 V0.2 发布目标未变更为已发布状态；当前单端范围决策见 [TASK-116](.dev/TASK-116_FIGMA_SCOPE.md)。

当前原型可只提供 Figma 文件运行生产预检，无需 Penpot 文件：

```powershell
.\.venv\Scripts\python.exe scripts/run_figma_pipeline.py examples/user-management-compact-search-v026 --output-dir artifacts/my-figma-run --figma-file <Figma文件ID> --profile v0.2.6
```

该命令保存九阶段 Core、Figma 原生计划和字节锁；实际写入 Figma 与原生复验仍需执行已校验的计划。旧双平台命令只用于历史复验。

完整目标见 [V0.2 自主持续开发计划](docs/DEVELOPMENT_PLAN_V0.2.md)：

- 提前建设18类组件，以及明确的变体、状态、尺寸和配置覆盖范围。
- 页面、Section、复杂表格模式和1920宽画布布局政策。
- 图片原型理解、带来源记录的设计默认值与模拟数据。
- 仅调用正式Registry的自动组装、规则驱动视觉修正。
- 用户选择目标平台；两平台能力分别通过发布验收。
- 阶段自动推进、测试、记录、提交、断点恢复和冲突处理。

当前 Figma 范围状态为 **IN PROGRESS**。Figma 侧组件证据、当前 Adapter 字节锁和新独立原型单端验收已通过；剩余 11 类组件尚未进入正式生产 Registry。旧版完整目标计划保留作历史背景，不作为当前 Penpot 工作队列。当前开发不意味着启动后台任务；未执行的检查不计为通过。

## 阅读入口

- [SKILL.md](SKILL.md)：Agent执行入口。
- [ARCHITECTURE.md](ARCHITECTURE.md)、[CONSTRAINTS.md](CONSTRAINTS.md)：已实现架构与冻结边界。
- [.dev/DEVELOPMENT_STATE.md](.dev/DEVELOPMENT_STATE.md)：公开版状态与后续方向。
- `core/`、`schemas/`、`validators/`：平台无关流水线与校验。
- `component-builder/`、`icon-manager/`、`registries/`：官方资产提取、同步与准入。
- `adapters/`、`examples/`、`tests/`、`releases/`：平台执行、输入、测试和版本快照。

第三方组件和图标遵循其上游许可证。仓库不含Arial、苹方等专有字体文件，不授予其使用或分发权。本项目尚未选择独立开源许可证；公开可见不等于授予开源许可。
