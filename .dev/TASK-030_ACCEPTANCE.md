# TASK-030 — Button 双平台字形与圆角诊断

日期：2026-10-13。范围：对 TASK-027/028 的实际原生 Button PNG 与锁定官方截图做来源绑定的像素诊断，不执行 Registry 准入。

`scripts/button_fidelity_diagnostics_v02.py` 先核验官方来源截图和两端候选 PNG 的 SHA256，再将透明 PNG 合成白底，分别统计文字区域、圆角边缘与非文字内部差异，并检查圆角边缘颜色是否仍属于锁定蓝色与白色的混合。结果在 `artifacts/task-030/button-fidelity-diagnostics.json`。

| 平台 | 文字区域差异 | 左/右字形亮像素 | 圆角差异 | 圆角非蓝白混合 | 非文字内部差异 |
|---|---:|---:|---:|---:|---:|
| Figma | 308 | 35 / 43 | 27 | 0 | 0 |
| Penpot | 303 | 53 / 40 | 42 | 0 | 0 |

两端原生 PNG 均可读为“查询”，两侧字形有可见像素且未贴到按钮边界。圆角差异属于蓝白抗锯齿覆盖差异的证据，不能凭此自动认定完整保真。字体 API 记录了原生默认字体绑定，但实际 CJK 回退字体身份仍未核实；诊断状态 `REVIEW_REQUIRED`、`nativeAdmission=NOT_RUN`、`releaseReady=false`。反例测试区分缺字、内部像素篡改和圆角异色。

Core 检查 171 项通过；Git diff 空白检查通过。
