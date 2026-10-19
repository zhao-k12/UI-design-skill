# V0.2 默认字体 DatePicker：Figma 单端质量核验

范围仅为 View UI Plus 1.3.24 `form.datepicker.date.selected` 固定静态配置：关闭面板、只读、不可清除、值 `2024-01-01`，211×32px。Figma 使用当前文件默认 Inter Regular 14/21。官方 Ionicons 日历轮廓图标在 Figma 中明确改编为已同步且哈希锁定的 Remix `calendar-line` 原生组件实例。

Figma 必须保留可编辑日期文字、原生主组件与真实关联实例。白底、1px `#DCDEE2` 边框、4px 圆角、`#515A6E` 文字和 `#808695` 图标均绑定来源变量。官方与 Figma 图片不缩放、不平移；Figma 透明像素合成白底。排除日期文字和图标区域后，背景与边框必须一致，仅四角抗锯齿允许至多 41 像素差异，最大通道差 4，其余像素完全相同。日期文字和图标区各至少 200、60 个深色像素，均需完整在范围内。独立原生读回、PNG/SVG 与候选一致，重复 PNG 逐字节一致；视觉复核绑定复验 PNG 哈希。

用户决定暂缓 Penpot，故 PASS 只表明 Figma 单端 QA。`admissionEligible=false`，不可登记正式 Registry 或宣称 V0.2 发布就绪。
