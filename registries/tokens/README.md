# Design Tokens Registry V0.1

`default.json` 是带版本的项目初始基线，覆盖 Color、Typography、Spacing、Radius、Border、Shadow，以及 `spacing.page`（Page Padding）、`spacing.section`（Section Gap）。额外的 Size Token 表达页面宽度、图标尺寸和字体几何值。

这些值用于页面区域的统一选择，不是官方组件视觉参数；官方组件内部参数必须在 TASK-006/007 从真实运行结果提取并通过保真检查。字体名称只是项目声明，本任务不检查字体安装情况；Adapter 阶段必须报告不可用字体，不能静默替换。

## 数据契约

使用 `schemas/token-registry.schema.json` 验证。Registry 有 registryVersion、name、provenance、tokens。每个 Token 的 ID 前缀必须与 type 一致，value 可以是本类型值，或同类型引用 `{ "token": "spacing.lg" }`。spacing.page 和 spacing.section 通过 role 标识语义；均为 spacing 类型。

Typography 描述 fontFamily/fontSize/fontWeight/lineHeight/letterSpacing；Border 描述 color/width/style；Shadow 是一组 offsetX/offsetY/blur/spread/color。组合值可以引用对应类别 Token。别名、组合引用都必须存在且无循环；未使用的坏引用也会导致 Registry 失败。

TokenRegistry 在创建时复制数据，给出只读版本、规范化 JSON 的 SHA-256 和独立副本；调用方修改源 JSON、snapshot 或 resolve 返回值不会修改实例。expected_version 不匹配产生 token_version_mismatch。本任务不创建完整任务 manifest 或 Migration，它们属于 TASK-017。

## UI-IR 使用和质量门

`validators.ui_ir` 保持仅检查契约语法；`validators.tokens` 先执行 UI-IR 契约检查，再验证 Registry 和引用。UI-IR 的逻辑结构、Token Reference 与内容保持不变，只有消费者通过 resolve 获取值。

- gap/padding/spacingToken → spacing。
- fill/colorToken → color；radius → radius；typographyToken → typography。
- stroke 可以保留 `{ color, width }`，也可使用 `{ "token": "border.default" }`。
- shadowToken 使用 `{ "token": "shadow.card" }`。
- fixed width/height 的引用只能解析为 size、spacing 或 radius 的正数，颜色或零不能用作固定尺寸。

UI-IR 增加 Border 引用和可选 shadowToken 是开发期的向后兼容扩展，既有 JSON 无需变更；版本仍为开发中的 0.1.0 契约。尚无已发布的 Adapter 消费者。

优先使用 Token Reference。组件实例以外显式填写的颜色、间距、padding、stroke 和 radius，必须是 Registry 已登记尺度中的值，否则报告 unregistered_visual_value；不会把它自动改成最近值。固定几何尺寸、opacity、缺省布局语义不是此检查的尺度匹配对象。组件和图标实例内部视觉、覆盖属性的合法性由后续资源/保真 QA 检查，此处不声称已完成。

只遍历节点的 layout/style，并递归检查 children 和 slots；业务 props 中名为 token 的内容不会被当作设计 Token。

## 执行

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m validators.tokens examples/user-management.ui-ir.json --report artifacts/task-003/token_qa_report.json
.\.venv\Scripts\python.exe -X utf8 -m validators.tokens examples/missing-token.ui-ir.json --report artifacts/task-003/missing_token_report.json
```

第二条故意失败，返回 1 并报告 missing_token、原始 Token ID 和 JSON Pointer 路径。不存在隐式 fallback。报告记录 Registry 版本及指纹；报告路径禁止与输入文档或 Registry 相同。报告默认按运行产物保存，不提交 Git。

错误还包括 invalid_token_registry、token_type_mismatch、token_cycle、invalid_token_value、token_version_mismatch。PASS 仅表示 Token 质量门成功，不代表资源登记、布局、原生组件或完整流水线通过。
