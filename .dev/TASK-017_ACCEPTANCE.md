# TASK-017 验收：PASS（2026-10-10，Asia/Shanghai）

V0.1 首次端到端验收通过。输入是用户选定并批准语义复核的冻结用户列表：姓名／状态／角色，三行数据。原型、批准 receipt、实际测量、布局选择、组件决策及内容契约均在 `examples/acceptance-prototype`。没有将姓名／邮箱／状态静默替换成另一套内容。

完整证据和最终报告：`examples/end-to-end-acceptance/final_qa_report.json`。Core 保存9个可恢复阶段；版本锁为 Skill 0.1.0、UI-IR 0.1.0、既有生产组件库快照0.1.0-dev、官方 View UI Plus 1.3.24 锁定来源、Remix Icon 4.9.1 锁定来源、Token／规则0.1.0、两平台 Adapter 0.1.1-content。发布使用独立目录，没有改写旧版本锁；说明见 `version-migration.json`。最终 UI-IR 保持相同：`94d539a316f9ac50af23726b705af8e5c89fd188dba9e99a8a0aee9195394bee`。

## 实际原生结果

| 检查 | Figma | Penpot |
| --- | --- | --- |
| 同一最终 UI-IR | PASS | PASS |
| 9项语义内容／49个逻辑节点 | PASS | PASS |
| 实际节点完整读取 | 90节点 | 92节点 |
| Input／Select／Button／Table真实实例 | 4 | 4 |
| 官方设置／下载图标真实实例 | 2 | 2 |
| 可编辑文字、表头、三行数据 | PASS | PASS |
| 栅格、流式位置、间距、字号、字体、颜色、溢出 | PASS | PASS |
| 完整原生 PNG | 1440×488 | 1440×488 |
| 实际视觉检查 | PASS | PASS |

[Figma 原生页](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9?node-id=49-3)。[Penpot 原生页](https://design.penpot.app/#/workspace?team-id=45145cff-4092-8110-8008-acf328e8a85a&file-id=91396aad-60c8-808b-8008-c0885ca79899&page-id=7e685f08-b6bc-80f5-8008-c39491c1701c&board-id=7e685f08-b6bc-80f5-8008-c394927d342f)。两份完整独立证据在对应 Adapter 的 `metadata/pipeline-acceptance`；保存原始回执、完整节点、PNG、实际执行脚本、来源捕获、独立实例导出及视觉检查记录。

首次截图背景透明，最终按锁定 Token 给 Page／三个 Section 加背景。两平台都原位只修改4个布局区域的 fill，无创建／删除，分别保持86／88个其他节点全部不变。完整前后回执保留。Penpot 已在刷新和恢复原有节点后独立导出，页面持久保存，没有重复创建。

Figma 当前6个实例 PNG 与当前主组件逐字节一致。4个 UI 来源的全部历史已记录属性、几何及13份文字 SVG 轮廓重新验证；新增观测的四边描边值只接受与历史 uniform strokeWeight 精确一致。历史 PNG 与当前导出存在317／150／139／1000个像素差异，全部位于已批准的独立向量边缘及文字／圆角区域，带外0，逐字保留检查通过。报告没有伪称历史 PNG 字节相同，没有添加聚合像素误差预算。

Penpot 4个 UI 实例 PNG 与已准入主 PNG 逐字节一致。两图标来源及实际平移后的有序路径精确符合既有 Float32 规则，SVG重现逐字节一致；原生边缘差异137／42像素，验证带外0。导出服务的原始超时和 PARTIAL 回执保留，只复用了同一 revision28、同实例／主节点状态的成功格式；最后实际补齐全部6个实例 PNG／SVG。

## 自动与反例验证

- 全项目389项 Python、102项 Node：PASS，0失败、0跳过。Core架构检查：PASS。
- 历史 Figma四类组件官方保真及 Penpot TASK-010 完整验收重新执行：PASS。既有准入来源和历史绑定代码没有被覆盖。
- 实际首次运行9阶段通过，再次运行复用全部9个字节绑定 checkpoint，最终布局／UI-IR一致。
- 映射变化从映射阶段恢复；相同最终 payload 不重建 Section。修改缓存布局会重跑对应阶段；版本变化阻止复用旧任务目录。
- 未批准／拒绝复核、伪造实际测量、遗漏／重复布局顺序、缺表头／数据、擅自替换表体均阻止原生预检。
- 原生读回反例覆盖：漏字段、按钮、Section、图标，错主组件／Flatten，非法 Variant／未登记 Icon，错栅格、大小、位置、间距、字体、背景，文字／组件溢出，旧 SHA、异页、缺 PNG、改数据，来源属性／轮廓改变及改 checkpoint。

Release Gate 的17项及额外实际视觉门均为PASS，详见最终报告的18项 `releaseGates`。不是用 Core PASS、预检 PASS 或用户批准代替实际原生验收。

## 能力边界与使用

入口和命令见 `SKILL.md`、`core/pipeline/README.md`。AI 提供来源绑定观察及显式判断；程序执行布局与质量门。当前实际双平台端到端实证为该冻结静态列表，正式库准入范围是四类固定 UI 状态和两份图标；五类 Pattern 有确定性布局测试。Task-015 的文字内容和六类 Cell 角色组合另有真实原生证据。

不包含自动 OCR、交互、业务逻辑、任意新组件／状态、响应式、复杂表格数据改写。资源真实性及 Missing 处理已实现，原生 Image 未准入。新设计、新来源、内容变更及目标文件必须具备对应真实测量、库引用和独立原生验收，不能照搬本次批准或截图。
