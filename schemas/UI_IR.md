# UI-IR V0.1 Contract

`ui-ir.schema.json` 是独立 JSON Schema，使用 [Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)。Python 使用 [jsonschema 的 Draft202012Validator](https://python-jsonschema.readthedocs.io/en/stable/validate/) 验证；Schema 不依赖 Python 或设计平台。

## 文档和节点

文档必须包含 `uiIrVersion: "0.1.0"`、`documentId`、非空 `pages`。每个 Page 包含有序 children。支持 Page、Frame、Section、Grid、Row、Column、VerticalStack、HorizontalStack、Text、ComponentInstance、IconInstance、Image、Divider。

节点 `id` 在整个文档（包括 slots）唯一，且区别于业务 props 中的 id。`name` 可选；`sourceIds` 可引用原型或 Page Tree 的来源 ID，后续完整性 QA 验证来源，不在本任务假造来源解析器。Page 只能在 pages 根列表中出现。

容器有 children；Text 必须有 text；ComponentInstance 必须有 componentId，可有 variant、静态 props 和 slots；IconInstance 必须有 iconId；Image 必须有 assetId 和 alt，可指定 contain/cover/fill 的 fit。实例节点没有自由 children，嵌套内容仅通过命名 slots 注入。支持 leading-icon、trailing-icon、label、control、content、actions 六个槽，槽值为非空节点数组；无内容时省略槽。

逻辑 ID 允许字母开头、字母数字以及 `.`、`_`、`-`，不保存平台引用。平台 metadata 必须保存在 Adapter 产物中，不在 UI-IR 增加字段。所有结构对象关闭未知字段；业务 props 是可嵌套 JSON 数据，但所有层级禁止带 figma/penpot 的键名。文本值可以出现平台名称，不把正常业务文本误作平台依赖。

## 布局

| 字段 | 契约 |
| --- | --- |
| width / height | `{ "mode": "fixed", "value": 1440 }`、fixed + Token、`{ "mode": "fill" }` 或 `{ "mode": "hug" }`；fixed 为正值，fill/hug 禁止 value |
| padding | top/right/bottom/left 四边，非负数或 spacing Token；单位为设计逻辑像素 |
| gap | 非负数或 spacing Token |
| alignment | main: start/center/end/space-between；cross: start/center/end/stretch |
| direction | horizontal / vertical；Row/HorizontalStack 固定 horizontal，Column/VerticalStack 固定 vertical |
| wrap | 布尔值 |
| gridColumns | Grid 必须为 24，其他布局可提供 1–24 的整数 |
| span | 1–24 的整数 |

布局不包含自由 x/y 坐标。省略属性的确定性默认语义：width/height 为 hug，padding/gap 为 0，alignment 为 start/start，wrap 为 false，span 为 24。Row、HorizontalStack、Grid 方向为 horizontal；其余容器为 vertical；叶节点 direction 不参与内部布局。Grid 按 children 次序排放，每个 child 的 span 定义占列数。Grid 的实际换行、空间计算、Fill/Hug 循环、溢出及 section 间距由 TASK-004/013 执行和检查，本任务不实现布局引擎。

示例指定页面固定宽度和四列 span=6。它只描述静态列表页，未加入交互、业务逻辑或响应式。

## 视觉与 Token

style.fill 是颜色，与 layout.width.mode=fill 完全分开；颜色接受 #RRGGBB / #RRGGBBAA 或 color Token。style.stroke 有 color 和非负 width，也支持 border Token Reference；shadowToken 使用 shadow Token Reference。radius 为非负数或 radius Token；opacity 在 0–1 范围。typographyToken、colorToken、spacingToken 使用对应类别 Token Reference。

统一 Token Reference 形式为 `{ "token": "spacing.md" }`，不允许附带临时 fallback。省略 style 表示不覆盖资源样式；容器不额外绘制 fill/stroke。布局默认值属于数据契约的执行语义，官方组件内部视觉仍由真实运行结果及 Registry 决定，禁止 Adapter 自行更改。

UI-IR 契约校验只验证 Token 引用语法与类别，**不证明 Token 存在**；已实现的 TASK-003 使用独立 Token 质量门验证 Registry 和 missing_token，详见 [Token Registry](../registries/tokens/README.md)。组件、图标、资产 ID 的可用性、保真、变体和槽位合法性由后续任务检查。示例组件/图标 ID 未登记，不可拿去输出真实设计实例或宣称设计 QA 已通过。

## 验证范围

JSON Schema 检查字段、类型、范围、节点变体和嵌套结构；`validators/ui_ir.py` 另外检查全局节点 ID 唯一性、平台字段及严格 JSON 输入（禁止重复键、NaN、Infinity）。成功仅表示 UI-IR 数据契约通过，不表示组件准入、资源可用、布局正确或 Final QA 通过。

```powershell
.\.venv\Scripts\python.exe -X utf8 validators/ui_ir.py examples/user-management.ui-ir.json
```

CLI 输出 scope=ui_ir_contract、PASS/FAIL 和带 JSON Pointer 路径的诊断；失败返回 1。不同语言的消费者可以复用同一 Schema，并补充相同的唯一性检查。版本不匹配直接失败，Migration 不在此任务实现。
