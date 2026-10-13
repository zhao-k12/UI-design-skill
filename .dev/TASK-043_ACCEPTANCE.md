# TASK-043 — V0.2 默认字体页面 Adapter 双平台原生验收

日期：2026-10-13。状态：PASS（仅 Adapter 契约样张）；完整原型到页面流水线与发布门仍未验收。

基于 TASK-042 锁定的同一 UI-IR（SHA-256 `3424375df6cc9625a62aa015097f40707b63675aa8d278346d680dd38df2e8ec`），在用户指定的 Figma 文件 `0vGWSRoLxBiVPXiZ8xJAX9` 创建页面 `163:2`、根框架 `163:3`；在替代 Penpot 文件 `57949053-620f-8001-8008-c804c8d61529` 创建页面 `4b3abcb2-3ae8-803f-8008-c86e5a61aac1`、根画板 `4b3abcb2-3ae8-803f-8008-c86e5af59ea8`。两端原生输出均为 1920×1080，包含自由文字标题“用户管理”和按顺序排列的 Button、Input、Select、Table 四个真实组件实例。独立读取确认标题分别使用 Figma Inter Regular 400、Penpot `sourcesanspro` regular 400；五个子节点的相对位置和尺寸逐项一致。

第一次 Penpot 运行在写入前发现绑定 ID 的两种形式：Button/Input 使用组件库 ID，Select/Table 使用组件主实例 ID。原生库读取确认了对应关系。按照 [TASK-043 架构冲突记录](TASK-043_ARCHITECTURE_CONFLICT.md)，Penpot Adapter 现于本地组件库中精确解析两种 ID，拒绝歧义，再以真实组件库 ID 核验创建的实例。没有改动 Core、已冻结 Registry 或 TASK-042 脚本；修正后的脚本和预检报告另存于 `artifacts/task-043/penpot`。第一次失败未创建 Penpot 节点。

两端各导出原生 1920×1080 PNG。Penpot 透明画布先合成到 Figma 的背景色后，对实际内容区域 `(0,0)–(1392,268)` 比较，平均 RGB 绝对差为 `0.875/0.808/0.702`（8-bit 通道）；没有可见内容缺失或文字裁切。Figma/Penpot 独立读取 JSON、原生 PNG、合成 PNG 与机器验收报告保存在 `artifacts/task-043`。报告 `status=PASS`、`issues=[]`、`releaseReady=false`。本样张按契约规定将控件紧贴排列，只验证 Adapter 翻译和默认字体，不代表正式页面布局。

Penpot 运行器 18 项 Node 测试通过，包含主实例 ID 正确解析与歧义拒绝；默认字体预检和 Penpot Adapter 定向 Python 测试通过。后续须以真实静态原型执行理解、结构、布局、映射、UI-IR、双端 Adapter 和最终 QA，才能评估 V0.2 页面能力。
