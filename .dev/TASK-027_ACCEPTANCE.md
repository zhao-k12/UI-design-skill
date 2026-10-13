# TASK-027 — Figma 默认字体 Button 原生候选

日期：2026-10-13。范围：在用户指定 Figma 文件中创建独立的 V0.2 Button 候选，并与锁定官方来源进行来源绑定的初步对照。候选不入 Registry。

## 实际原生结果

- 目标文件 `0vGWSRoLxBiVPXiZ8xJAX9` 新页面 `135:14`，主组件 `135:15`、Label `135:16`、审核实例 `135:18`，均与历史组件隔离。
- 从官方 View UI Plus primary/default Button 的真实 Component IR 取得 60×32、背景/边框 `#2D8CF0`、白色文字、左右 padding 15、圆角 4、边框 1、文字“查询”、字号 14、行高 21、字重 400。新原生文字使用 TASK-024 实测默认 Inter Regular。
- 创建 11 个局部变量并绑定填充、描边、间距、圆角、高度、字号、字重和行高；组件具有可编辑 `Label` TEXT 属性，审核实例仍关联主组件。独立 API 读取确认几何、变量及实例关系，独立原生 PNG 中内容完整。
- 来源与候选比较 11 项检查通过。透明原生 PNG 合成白底后，在来源文字区域 308 个差异像素、圆角边缘 27 个、其他区域 0 个差异像素。文字/边缘差异仍需新版本完整字形和边缘保真审查；`status=CANDIDATE_REVIEW`，`nativeAdmission=NOT_RUN`，`releaseReady=false`。
- 原始创建、独立读取、原生 PNG 和对照报告在 `artifacts/task-027/figma`；SHA256 及节点绑定在 `adapters/figma/metadata/button-default-font-candidate-0.2.0.json`。

## 验证与限制

`adapters/figma/button_candidate_audit_v02.py` 的反例检查覆盖错误文字/字体、非文字颜色和像素改变、外来节点及虚假准入。像素分区只是定位差异的诊断，不是可凭此自动准入的容差。后续仍需独立边缘规则和有效中文字形证据。

Core 检查 160 项通过；Figma 候选生成脚本通过 Node 语法检查；提交前 Git diff 无空白错误。

Penpot 插件在本阶段返回 “No Penpot instance connected”；已请求重新连接。Penpot Button 候选与双平台新版本准入均未执行。
