# TASK-025 — 新默认字体与官方组件来源审计

日期：2026-10-13。范围：分析最小 Button/Input/Select/Table 来源与两个目标字体的兼容性，保存证据并为后续测量设置阻断门。

## 实际检查

- 使用 TASK-023 两次真实官方浏览器提取的第一份 Component IR（Button/Input/Select）及锁定的两列表格 Component IR，读取可见文字/placeholder 样式和 CSS 声明。平台目标绑定来自 TASK-024 实测 Adapter Metadata。
- 两平台对四类组件均未匹配官方 CSS 字体栈；各组件需要新测量：Button 1 组、Input 1 组、Select 1 组、Table 2 组。审计输出 `REMEASURE_REQUIRED`，`nativeAcceptance=NOT_RUN`、`readyForPageGeneration=false`、`releaseReady=false`。
- 工具拒绝缺失/重复组件、不可见或缺样式的文字、错误平台绑定与伪造准入；不修改来源 IR、Registry、Core 或历史记录。
- 审计命令：`rtk proxy .venv/Scripts/python.exe -X utf8 scripts/font_source_compatibility.py --output artifacts/task-025/source-font-compatibility.json`。
- 新增 6 项来源兼容性测试；core 分组 151 项 PASS，日志保存在 artifacts/task-025/core。

## 依赖与下一步

字体选择和旧 Fidelity 的冲突记录在 [TASK-025_ARCHITECTURE_CONFLICT.md](TASK-025_ARCHITECTURE_CONFLICT.md)。当前完成了冲突证据，不宣称新组件已完成原生测量或准入。
