# TASK-033 — 默认字体 Input 双平台原生候选

日期：2026-10-13。状态：CANDIDATE_REVIEW；原生 Fidelity Gate 与 Registry 准入均未执行。

## 来源与候选

- 官方 View UI Plus `form.input.default.medium` 的静态来源为 240×32、空值、占位文字“请输入姓名”、白底、`#DCDEE2` 1px 内侧描边、4px 圆角、左右 7px / 上下 4px padding、占位色 `#C5C8CE`，字号 14、字重 400、行高 21。来源锁定在 TASK-023 `component_ir.json` 和浏览器截图。
- Figma 目标文件 `0vGWSRoLxBiVPXiZ8xJAX9` 的主组件 `141:3` 使用 Inter Regular 400；Penpot 新目标文件 `57949053-620f-8001-8008-c804c8d61529` 的组件 `4b3abcb2-3ae8-803f-8008-c811d08712ea` 使用 sourcesanspro regular 400。两端均有独立实例与结构读取。
- 两平台第二次原生 PNG 导出各自与首次 **逐字节相同**；独立再读确认组件、实例、文字、字体与 240×32 几何不变。实际图片与读取记录保存在 `artifacts/task-033`，提交的 Adapter Metadata 锁定其 SHA256。
- 逐像素白底合成对比：除占位文字区域与四个 5×5 圆角区外，两个候选的非文字区域与官方截图无差异。五个字各有可见灰色字形；人工视觉复核确认文字完整、无豆腐字或裁剪。圆角差异仍需在独立保真门中定义容差与颜色约束。

## 自动检查与边界

`scripts/default_font_input_candidate_audit_v02.py` 核对官方来源、结构、默认字体绑定、实例关系、重复导出、像素区域与哈希绑定的视觉复核。结果是两端 `CANDIDATE_REVIEW`，由 `scripts/lock_default_font_input_candidate_v02.py` 写入两端候选 Metadata。对应测试包含真实证据核验、非文字区域改动和缺少首字的负例。

Input 尚未进入 V0.2 Registry，不能生成正式页面实例。中文实际回退字体身份仍为 `UNVERIFIED`。下一步是独立 SVG/文字与圆角测量、原生保真门及内容范围决策；不沿用 Button 的准入结论。
