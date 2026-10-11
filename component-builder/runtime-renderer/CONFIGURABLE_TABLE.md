# 可配置官方表格来源提取

TASK-018 提供开发工具，用于为新的静态表格配置取得真实官方来源。它没有将新表格加入正式 Registry，也不允许已有 Table 实例直接覆盖正文。原生组件制作、双平台保真和新原型语义复核仍需单独执行。

```powershell
node component-builder/runtime-renderer/configurable-table-extract.mjs --request examples/table-source-request.json --output artifacts/my-table-source
```

输出必须是项目 artifacts 内尚不存在的目录。工具拒绝覆盖既有证据或通过 junction 逃出 artifacts。请求必须只包含 version、containerWidth、columns、records；示例另见 `examples/table-source-request-four-columns.json`。

- version 为 0.1.0；整数容器宽度 128–3840。
- 1–12 列，每列明确声明 key、title、width；key 唯一，width 为至少 64 的整数，总宽度严格等于容器宽度。
- 1–50 行，每行键集合必须与列完全一致。单元格为非空纯文字字符串，最多 512 个 UTF-16 code units，不含控制字符。数值、日期等应先在原型中明确其显示文字。
- 列顺序决定输出顺序；记录对象键顺序不影响配置摘要。不同配置得到独立逻辑 ID，不能冒用已经准入的 data.table.default。
- 本阶段只提取不显示表头的官方正文，与现有 Table Body 路线一致；title 保存在官方 columns 属性中，后续表头组装需要独立测量和来源核对。

工具保持锁定 View UI Plus 1.3.24 的源码、CSS 和官方 Vue Table 实现。配置通过 esbuild 虚拟 JSON 模块传入，冻结的 table-cases.json 不被覆盖。真实 Chromium 中逐行核对可见 td 内容、容器宽度以及官方解析后的 columns/data，保存 Component IR、PNG、runtime manifest、请求和观察回执。隐藏的“暂无筛选结果”行保留在原始 DOM 提取中，但不算可见数据行。

`table-source-report.json` 的 PASS 仅表示官方来源提取通过；fidelityGate 和 nativeExecution 均为 NOT_RUN，productionAdmission 为 false。失败保存 FAIL，不能将其当作可落地设计。

官方 table.vue 使用 random(6) 创建 ivu-table-column-* 类名。原始 IR 保留真实随机类名及原始 SHA，不要求两次 IR 字节相同。重复提取测试仅在比较副本中按首次出现顺序替换这一类生成名称，仍严格比较其余全部结构、几何、样式、文本、关联，以及逐字节相同的 PNG；不用于平台保真准入。

## 带表头表格来源（TASK-020）

独立开发入口保持正文版本锁不变：

```powershell
node component-builder/runtime-renderer/headed-table-extract.mjs --request examples/table-source-request.json --output artifacts/my-headed-table
```

输入契约与正文工具相同，使用官方 showHeader=true，输出独立 data.table.headed 身份。核对真实列标题、正文、官方解析属性、容器宽度并保存表头实测矩形；官方表头列宽存在小数，不将配置整数宽度当作实际矩形。工具输出仍仅表示来源提取。TASK-020 两份冻结配置已另行完成双平台原生制造、完整保真和真实实例验收，正式准入仅见显式 component-library-0.3.0；其他请求仍须独立完整验收。记录见 .dev/TASK-020_ACCEPTANCE.md 和 releases/component-library-0.3.0/README.md。
