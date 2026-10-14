# TASK-051 — 固定 Table Body 与来源表头组合

日期：2026-10-14。状态：RESOLVED（沿用既有表头组合契约的兼容修正）。

当前设计：V0.1 把三列表头作为已核对的来源文案保存在 `content.items[].props.headers`，由 `table_header.compose` 生成独立原生 Text 表头；Table Body 保留官方实例。V0.2.3 Registry 将 Table Body 限定为固定内容，要求传给官方实例的 `props` 为空。

冲突原因：装配器先校验固定 Table Body 的空 `props`，之后才从该实例的 `props.headers` 提取独立表头，因此 V0.2 在 `component-assembly` 阶段误判来源表头为组件内容覆盖。

影响：若删除 `headers` 会无声丢失原型三列表头；若放宽 Table Body 的固定内容范围则破坏已验收的官方组件限制。

决策：在固定 Table Body 校验之前仅提取来源表头声明，保持其证据验证与 `table_header.compose` 流程；官方 Table 实例仍以空 `props` 和固定三行数据验收。非固定 Table 的旧流程保持原有行为。该修正不改变 UI-IR 结构或组件 Registry，双版本回归和 V0.2 完整预检必须通过。

## Adapter 版本路由

当前设计：V0.1 Figma 走 `content_compiler`，读取 V0.1 字体和组件内容绑定，并声明 `0.1.1-content`；V0.2 固定内容实例已经在 Core 装配时归一化为空 `props`/`slots`。Penpot 的无内容计划自然声明基础 `0.1.0`。

冲突原因：生产 CLI 对两个 Profile 都强制调用 V0.1 Figma 内容编译器，并沿用 `0.1.1-content` 版本锁；V0.2 Registry 指纹不同，因而出现 `content_registry_migration_required` 与 Adapter 版本不一致。

影响：Core 通过而双端 Adapter 预检失败，不能把该失败误作原生组件不保真。

决策：V0.2 明确调用现有基础 Figma 编译器，两端版本锁均为 `0.1.0`；V0.1 继续使用内容编译器和 `0.1.1-content`。固定内容的两端原生保真证据及绑定仍由现有 V0.2 Registry/Metadata 约束，最终真实页面仍需单独原生验收。
