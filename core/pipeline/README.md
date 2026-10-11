# 静态 UI 流水线

入口是项目根目录的 `SKILL.md`。AI 阅读原型、提供来源绑定的语义观察和组件选择；程序验证这些判断并执行布局。当前不自动调用模型或 OCR，不生成交互。

准备输入目录：原型文件、`observations.json`、匹配当前分析指纹的人类 `review.json`、`layout-plan.json`、`decisions.json`、`content.json`、`source-geometry.json`、`runtime-measurements.json` 和 `versions.json`。完整实际样例在 `examples/acceptance-prototype`。语义复核批准只允许冻结对应的分析；原型改变后重新复核。不得把样例批准记录用于另一份原型。

布局按标准 Pattern 和 24 栅格运行，测量必须绑定独立实际来源的文件哈希和逻辑节点。组件保持已准入来源尺寸，在 Cell 内组合标签、控件、图标和内容；不会为填满 Cell 拉伸官方组件。Table 的表头用来源列宽构造可编辑原语，表体保持真实实例。当前三行静态数据须等于已准入表体，改变数据会返回 Unsupported。

## 运行与恢复

```powershell
cd F:\zo2026\ui-design-skill
.\.venv\Scripts\python.exe -X utf8 scripts/run_pipeline.py examples/acceptance-prototype --output-dir artifacts/my-design --figma-file 0vGWSRoLxBiVPXiZ8xJAX9 --penpot-file 91396aad-60c8-808b-8008-c0885ca79899
```

这一步保存每个阶段的 JSON、标注 HTML、版本 manifest 和 checkpoint，并为两平台生成预检计划。它不写入设计软件，不代表最终验收。再次运行同一命令复用输入和字节均未改变的阶段；首个改变的阶段及其下游重新执行。修改映射后还须更新内容契约的映射指纹；组装保留 Cell ID/box，仅声明受影响的 Section。版本或程序变更必须使用新的任务目录，不能自动迁移已有锁。

生产 Registry 目前准入 Input、Select、Button 和 Table 表体的固定默认状态，以及设置、下载两份 Remix 图标。样例绑定到上面两个已有设计文件。其他文件需要先取得真实库引用并通过 Adapter 预检，不能复制样例的平台 ID。额外组件、状态或资源按 Missing／Review／Unsupported 阻止依赖阶段。

## 原生执行与最终验收

Figma 主机通过已发现的能力运行 `adapters/figma/runtime.js` 和 `content_runtime.js`，消费预检计划的一个 page；保存实际执行回执及全部创建节点，随后独立读取全树并导出原生 PNG。使用 Figma 插件能力时遵守该能力的操作指南。

Penpot 用公开插件 SDK 执行同一 UI-IR。主机入口：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m adapters.penpot.host.pipeline_server --pipeline-dir artifacts/my-design --target-file 91396aad-60c8-808b-8008-c0885ca79899 --output-dir artifacts/my-design-host --port 57831
```

安装或打开该主机提供的插件地址后，生成独立页面并读取、导出。恢复既有页面用 `--candidate-readback` 指向实际执行回执，不再次创建。导出服务超时保留原始 PARTIAL 回执；`--previous-instances` 只允许同一文件 revision 和相同实例／主节点状态的成功格式复用。主机只监听本机 loopback，结果保存项目 artifacts。

原生证据保存在 Adapter 侧，Core 不读取平台节点 ID。最终检查要求同一 UI-IR、完整节点账本、真实主组件关联、可编辑原型内容、准确流式布局／栅格、合法字号和间距、无溢出、完整原生 PNG及实际视觉复核。Figma 历史原生像素若变化，必须重新证明来源全部属性和文字 SVG 轮廓不变，当前实例 PNG 等于独立当前来源，差异只在已批准的独立向量边缘及文字／圆角范围内；不增加像素误差预算。

首次冻结列表的独立证据已保存在两个 Adapter 的 `metadata/pipeline-acceptance`。实际最终检查命令：

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/finalize_pipeline.py --run-dir artifacts/my-design --source-dir examples/acceptance-prototype --figma-evidence adapters/figma/metadata/pipeline-acceptance --penpot-evidence adapters/penpot/metadata/pipeline-acceptance
```

它重新检查保存的实际证据及当前版本锁，输出 `final_qa_report.json`。使用示例证据要求本次最终 UI-IR 与已执行的冻结列表完全相同；新设计必须提供新执行、独立 capture、保真和实际视觉复核证据。不能手工把预检 PASS、Core PASS 或缺失导出改成原生 PASS。

## 验收范围

首次端到端列表是“姓名／状态／角色”，三行数据、9 项语义内容、4 个 UI 实例、2 个图标；两平台都保持原生可编辑。五类标准 Pattern 有确定性布局测试，当前双平台端到端实证为列表页。Task-015 的受支持文字内容和六类 Cell 角色组合另有独立原生验收；其他内容变化仍需对应来源与实际验收。

Image 的文件真实性、尺寸和 Missing 处理已实现；原生 Image 生成未准入。复杂表格数据改写、交互、业务逻辑、响应式和任意新组件不属于当前已验收范围。
