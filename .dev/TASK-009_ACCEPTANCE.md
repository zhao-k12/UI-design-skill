# TASK-009 实际验收：PASS

验收日期：2026-10-07（Asia/Shanghai）。采用用户批准的 AD-017 证据约束保真规则 0.2.0；没有将规则批准、诊断 SVG 或测试 fixture 当作通过。

| 验收项 | 结果 | 实际证据 |
| --- | --- | --- |
| Button / Input / Select / Table 官方来源保真 | PASS | `registries/components/fidelity-reports.json` 的四份 production 报告；`metadata/fidelity-proof-bundles.json` 保存原生与来源输入哈希 |
| 几何、paint、内容、字体及基线 | PASS | 三个既有候选和 Table 的独立原生 capture；完整字形、精确横向原点、实际 DOM baseline；箭头逐点六位有效数字序列化核对 |
| 栅格差异范围 | PASS | Native PNG 差异分别 317 / 675 / 311 / 2415；独立边缘带外和允许区域外全部 0。Table 非文字区域在 native PNG 与 browser SVG 中均 0 差异 |
| 实际 Registry 准入 | PASS | 四个 active 静态组件，Figma 引用 18:5 / 12:8 / 12:15 / 28:3；其他六个条目仍 planned |
| 固定 UI-IR → 原生列表 | PASS | `examples/adapter-fidelity-acceptance.ui-ir.json`；Figma page 35:2、root 35:3；34 个逻辑节点、76 个创建节点 |
| Component / Icon 真实实例 | PASS | 六个 INSTANCE：四个 UI 组件、两个官方 Remix Icon；独立读取真实 mainComponent 引用，Table 九个 Text 可编辑 |
| 装配后的主组件像素 | PASS | 四个实际实例重新导出的 PNG 与已准入主组件逐字节及逐像素相同，changedPixels 全部 0 |
| 页面截图与结构 | PASS | 独立原生 PNG 1440 × 496；节点类型、尺寸、Fill/Hug/Fixed、Grid24、gap/padding、字体、文字和页面边界回读一致；截图目视无重叠/缺失 |
| 正反例和回归 | PASS | 235 项 Python、55 项 Node；错误内容/字体/偏移、擦除薄字形、错误边框、准入证据缺失、假实例/主组件替换均拒绝；Core 架构检查通过 |

页面：[Figma 实际验收页](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9?node-id=35-3)。账号与 Temporary 团队沿用已批准目标。

Table 使用官方真实 `showHeader=false` 静态变体，三行三列中文数据；列标题属于 UI-IR。同色连续 cell 下边框按实际几何并集输出，底部 `::before` 来自已哈希验证的官方 CSS。没有改变官方 CSS/字体文件，也没有用截图、隐藏文字或参考覆盖层拼出组件。字体绑定复验只替换原字体栈中的 CJK fallback，保留官方 Latin strut；临时样式表和 FontFace 完整移除，参考恢复且截图相等。

历史候选、失败实验和原始参考保留。旧 smoke 的 Registry 输入哈希因准入发生迁移，不能直接作为当前完整验收；当前新 UI-IR、页面及最终 QA 均绑定新 Registry 指纹。

验收仅证明 TASK-009 的固定静态列表骨架。任意 props/slots 注入仍明确 Unsupported；其他计划组件、Penpot 和 TASK-017 的完整双平台 Release Gate 未通过，本项目仍为 0.1.0-dev，不宣称 V0.1 Ready。依用户要求，本次不进入 TASK-010。
