# Component Registry V0.1

TASK-005 提供逻辑组件契约与跨平台引用查询机制。经用户在 2026-10-05 明确确认，真实双平台组件定位在 TASK-007 之后验收；当前契约与查询测试通过可以进入 TASK-006。完整决策记录见 .dev/DEVELOPMENT_STATE.md。

## 当前内容

catalog.json 覆盖 Button、Input、Select、DatePicker、Table、FormItem、Pagination、Card、Tabs 共 9 类、10 个逻辑 ID（Button 有 primary/default 两项）。所有条目均为 planned，生产 active 数量为 0。

planned 描述是待实现的调用目标，不能创建实例；当前 variants/slots 是待验证的接口计划，不表示官方组件已有这些能力。正式登记前必须从真实组件确认它们。不存组件图形、视觉参数或平台 ID，不创建任何临时替代组件。

## 契约与职责

| 文件/模块 | 内容 |
| --- | --- |
| schemas/component-registry.schema.json | 平台无关 Registry 字段、逻辑 ID、类型、层级、状态、变体、槽位和保真证据引用 |
| core/component-resolver/registry.py | inspect/resolve，保真报告引用一致性、版本快照和未知/未就绪/弃用处理 |
| schemas/component-bindings.schema.json | Adapter Metadata 中的平台、版本、逻辑变体与原生组件引用 |
| adapters/figma/metadata/component-bindings.json | 该平台拥有的引用；当前为空 |
| adapters/penpot/metadata/component-bindings.json | 该平台拥有的引用；当前为空 |
| adapters/component_bindings.py | 按逻辑 ID 和变体读取该平台的引用，不调用平台 API |

Core 的 resolve 返回逻辑选择及描述，不返回设计软件引用。只有 Adapter 查询返回 fileReference/componentReference；两者是平台拥有的不透明引用，其格式和物理对象验证由后续对应 Adapter 定义。kind 必须为 component，不能把 Rectangle、Text 或 Instance 当作组件母版登记。

Bindings 必须绑定 Registry 的规范化 JSON SHA-256、libraryVersion、sourceVersion 和对应的保真报告哈希。未知组件、未声明变体、跨版本引用、Scope 不一致均失败，不做 fallback。文件路径与具体引用不进入 Core UI-IR。

## 准入与证据边界

planned 不可 resolve；active 必须加载 fidelity.reportId 对应的报告，并核对报告 SHA-256、PASS、Logical Component ID、Component Type、全部声明变体、Component IR 哈希、Scope 和 Source Version。sourceVersion=unresolved 不允许 active。

哈希算法为 UTF-8、ensure_ascii=false、键排序、紧凑分隔符的规范化 JSON，而非原始文件字节。Registry、输入报告及返回值均用快照隔离；修改调用方对象不能改变已建实例。

此处只验证证据的关联与一致性，不执行浏览器测量、几何保真或截图差异，也不认证报告来源。TASK-006/007 必须提供真实运行和质量门产生的报告，不得手写 PASS 代替；对应平台 Adapter 后续必须确认引用确实指向原生 Component。它们都是尚未完成的验收项。

deprecated 描述保留，禁止新建实例；历史实例的引用保留与恢复由后续版本管理/Adapter 处理。

## 测试隔离

单元测试只在内存构造 scope=test-fixture 的证据与平台引用，并显式打开 allow_test_fixtures。默认生产 API 和 CLI 拒绝这类 Registry，测试结果不能作为真实保真证据或平台存在性证据。生产 Metadata 不包含测试引用。

查询错误包括 missing_component、component_not_ready、deprecated_component、invalid_component_variant、missing_component_reference；证据错误包括 missing_fidelity_evidence、fidelity_not_passed、fidelity_variant_mismatch、fidelity_evidence_mismatch、fidelity_source_mismatch；引用错误包括 binding_version_mismatch、binding_fidelity_mismatch、platform_mismatch 和 binding_scope_mismatch。

## 执行

```powershell
.\.venv\Scripts\python.exe -X utf8 -m validators.component --report artifacts/task-005/component_registry_qa_report.json
```

默认校验生产 catalog 和两份生产 Metadata，输出 scope=component_registry_contract。报告的 PASS 仅表示本任务契约一致，liveDualPlatformAcceptance 仍为 DEFERRED；不会用空引用和 planned 描述宣称生成了真实设计稿。
