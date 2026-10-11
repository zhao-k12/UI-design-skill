# TASK-018 — 可配置官方 Table 来源提取

2026-10-10。用户在 V0.1 完成后继续要求开发；按已提出的“更多表格数据和列配置”方向推进。此任务完成官方来源工具，TASK-019 接续原生组件制作与双平台准入。架构依赖、正式 Registry 保真准入条件不变。

当前已有 Table Body 与三行“姓名／状态／角色”绑定。新配置不能改写这一来源或绕过 Unsupported 门。新增工具独立调用锁定的官方 Vue Table、CSS 和真实 Chromium，为每个配置提取新的 Component IR 和截图，不重写历史基线，不模拟平台输出。

## 实现与验收

| 检查 | 结果 |
| --- | --- |
| 严格列与行契约、固定列宽总和、完整键集合、非法属性拒绝 | PASS |
| 配置摘要、逻辑 ID、列顺序与原始输入不变 | PASS |
| 两列两行、不同列宽的真实官方 DOM／解析属性／截图 | PASS；720 × 96 正文 |
| 四列四行、不同列宽的真实官方 DOM／解析属性／截图 | PASS；960 × 192 正文 |
| 同配置重复提取截图逐字节相同，其余结构、几何、样式与内容一致 | PASS；原始随机列 CSS 类名保留，仅比较副本按关联顺序规范化 |
| 输出目录仅限 artifacts 内新目录；拒绝覆盖已有文件和已有来源证据 | PASS |
| 原有官方三组件提取、源码锁与全 Node 回归 | 106 / 106 PASS |
| 流水线及原有双平台 Release Gate 回归 | 10 / 10 Python PASS |
| 新增请求／程序字节指纹后针对性重跑 | 4 / 4 Node PASS |
| 新表格 Figma / Penpot 原生组件及保真准入 | NOT_RUN；TASK-019 |

## 证据与用法

[用法](../component-builder/runtime-renderer/CONFIGURABLE_TABLE.md)包含命令与输入范围。

`examples/table-source-acceptance/two-column/` 和 `four-column/` 保存实际 request、cases、可见 DOM 观察、Component IR、原生浏览器截图、runtime manifest、extraction report 和来源回执。`proof-manifest.json` 绑定这些文件及实际程序 SHA；`validation-summary.json` 记录本次检查范围。

原始失败 `artifacts/task-018/debug-1` 保留：官方隐藏空结果行初始被错误计入数据行。按 computed visibility 与真实高度核对可见行后通过。另一次重复性测试暴露 table.vue 的 random(6) 列类名；未改官方源码，未修改原始 IR，像素逐字节一致。

## 范围

工具契约接受 1–12 列、1–50 行、整数固定列宽和非空纯文字单元格；真实来源实证覆盖两列与四列案例。正文使用官方 showHeader=false，表头尚未新增原生实证。数值格式化、空表、交互、render 回调及复杂单元格不在本任务范围。

来源提取 PASS 不代表生产可用：所有新回执明确 nativeExecution=NOT_RUN、fidelityGate=NOT_RUN、productionAdmission=false。V0.1 现有原生能力及历史验收继续保留。下一任务制作两个新正文原生组件并实际验证，之后才可登记供映射选择。
