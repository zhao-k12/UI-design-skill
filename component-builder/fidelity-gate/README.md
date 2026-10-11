# Component Fidelity Gate 0.1.0

运行：

```powershell
.venv/Scripts/python.exe -m validators.visual artifacts/task-006 --candidate-dir artifacts/native-captures --output-dir artifacts/task-007
```

不提供 candidate-dir 时保存真实 WARNING，而非构造候选或 PASS。PASS 退出 0，WARNING/FAIL 退出 1。输出只允许在独立 artifacts 子目录；原始参考保持不变。

候选由 Adapter 导出，每个逻辑组件为 `<logicalComponentId>.json` 和同名 `.png`。JSON 契约：

- scope 为 production；测试专用数据为 test-fixture，不得入正式库。
- evidenceKind 为 native-design-capture。
- logicalComponentId、variant、state、props、content、fixtureContext、sourceVersion 与实际参考相同。
- capture 包含独立 captureId、exporterVersion、nativeEvidenceSha256（Adapter 保存的原生导出证据 SHA256）。平台对象引用仍只保存在 Adapter Metadata，不放入此中立契约。
- measurements 包含 rootBounds 与按参考可见节点 path 映射的 nodes；每个节点包含 bounds、computedStyle、textRuns、pseudoElements、value。字段结构见 validators/visual/fidelity.py 的 measurement；该函数只导出期望观察，不能用作候选测量器。Adapter 必须实际读取原生对象、记录映射和 Unsupported，不能复制期望值伪造测量。
- rasterContext 为 deviceScaleFactor（与参考相同）和 background=white；screenshotSha256 为实际独立 PNG 的 SHA256。

几何与列出的样式严格相等，不缩放截图、不扩大容差、不猜测 auto/normal。此初版要求 Adapter 提供已核实的对应样式表达；不同表达但无法证明等价时不能自动 PASS。文字范围、伪元素及输入值也比较；节点缺失或多余均 FAIL。

截图检查包括 RGBA 四通道、实际尺寸、文件哈希与独立文件来源。完全匹配才能 PASS。只有参考实际文字矩形内、单通道差异不超过 16 的像素可以标为文字抗锯齿 WARNING，仍不可准入；其他像素差异 FAIL。尚未实现自动证明跨字体/设计软件的抗锯齿等价，因此不放宽成 PASS。

component_fidelity_report.json 保存总状态和每组件结果。每组件报告的 componentIrSha256 是规范化单组件 IR 哈希，与 TASK-006 提取报告的整文件原始哈希不同；Registry 的 proof 应使用单组件哈希。正式 Registry 要求 PASS、admissionEligible=true、完整 gateVersion、原生 capture、比较检查及截图哈希，仍须由 Adapter 验证原生证据真实性和组件存在性。JSON 哈希只能证明一致性，不能认证外部来源。

当前没有生产 native capture；Button/Input/Select 的结果均为 missing_design_candidate WARNING，正式 Registry 保持 0 active。AD-016 的真实双平台验收仍待执行。测试的独立合成 PNG 只验证比较器行为，不是原生组件验收。
