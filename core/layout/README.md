# Layout Engine V0.1

本模块从已明确的 Layout Tree 计算 Layout Skeleton，不读取原型语义、不选择组件、不输出平台对象。TASK-013 将负责从冻结 Page Tree 选择布局；本任务仅提供其确定性执行器和标准结构模板。

## 输入与输出

输入契约位于 `schemas/layout-tree.schema.json`：layoutTreeVersion=0.1.0、pattern、一个根 Page。容器支持 Frame、Section、Grid、Row、Column、VerticalStack、HorizontalStack；布局叶节点为 Cell。Cell 是尚未映射组件的布局占位，不是 UI-IR ComponentInstance，也不是伪造的设计组件。

Layout Tree 不接受 x/y 坐标。输出的位置由引擎计算，使用页面绝对坐标、设计逻辑像素，最终保留六位小数。Skeleton 保存 id、type、role、sourceIds、box 和 children，不修改原树。结果包含引擎版本、Registry 版本和 SHA-256，可独立保存为阶段产物。

Cell 的 Hug 尺寸必须来自 measurement 的内容盒 width/height；若额外声明 padding，外盒会加上它。measurement.source 必须说明 test-fixture 或 runtime 及 reference。Fixed 尺寸不需要内容测量，Fill 尺寸必须有父级分配值。不能通过猜测字符宽度或组件内部参数得到尺寸。

`examples/user-management.layout-tree.json` 的所有尺寸来源均为 **test-fixture**，只用于执行器验证，不是官方组件或真实浏览器测量。真实组件测量及保真仍属于 TASK-006/007，最终设计必须经过 UI-IR 和 Adapter。

## 确定性规则

- Fixed 使用显式正数或可解析的几何 Token；Fill 使用有限父空间；Hug 根据测量和子布局计算。主轴 Hug 与子 Fill 的尺寸循环报告 unbounded_fill。
- 纵向/横向 Stack 按 children 的原始顺序排列。默认方向、尺寸、padding、gap 和 alignment 与 UI-IR 契约一致。
- 主轴 Fill 扣除固定/Hug 子项、声明的最小尺寸和 gap 后，平均分配剩余空间；不把负剩余空间偷偷压缩为较小组件。
- main 对齐支持 start/center/end/space-between；cross 支持 start/center/end/stretch。固定交叉尺寸不会被 stretch 改写。
- Wrap 可以按横向或纵向主轴换行，需要有限主轴尺寸。每行保留原顺序，以该行最大交叉尺寸和 gap 排列下一行。Wrap + 主轴 Fill 需要明确的最小尺寸（field 默认用 size.field-min）；不猜测 Fill 的换行基础。
- 24 Grid 的单位列宽为 `(内容宽度 - 23 × gap) / 24`，span 宽度为 `单位列宽 × span + (span - 1) × gap`。span 累计超过 24 时，只有 wrap=true 才换行。
- Grid 高度 Hug 时，每行取最大已测量子高度；高度有界时平均分配行高（扣除行 gap），检查子项是否超出分配。Grid 宽度 Hug 时，从有可确定自然宽度的子项推导最小列单位；Fill 子项不参与猜测自然宽度。
- 页面直接 Section 之间的距离必须符合 spacing.section。role=field 的宽度至少 size.field-min=160，此值是项目布局政策，不是官方组件参数；constraints.minWidth 只能提高该阈值，不能绕过项目最小宽度。其他节点也可声明 constraints.minWidth/minHeight。
- 显式 spacing/几何 Token 沿用 Registry 校验；非实例区域的原始视觉值遵守已登记尺度。Core 不接触设计软件 ID 或 API。

## V0.1 明确边界

Grid 采用 horizontal、start/start；需要其他对齐时使用内部 Stack。不接受非 Grid 的 gridColumns 或非 Grid 直接子项的 span。

Wrap + 交叉轴 Fill 会报告 unsupported_wrap_cross_fill：该组合需要明确的行测量规则，V0.1 不自动估计。缺失测量、无界 Wrap、未知 Token、尺寸循环及不支持的组合均失败，禁止继续使用 Skeleton。

布局深度上限为 12；同类型单子项包装产生 unnecessary_nesting warning，不自动删节点或改变语义结构。warnings 为可审查提示；error 会使 QA 为 FAIL，并返回 skeleton=null。CLI 失败时也会清除该目录以前的可用 Skeleton，避免沿用过期成功结果。

本任务不做文字排版测量、字体替代、完整响应式、交互、组件映射或最终视觉 QA。含测量来源声明不代表运行来源已认证。

## 标准 Pattern

`patterns.instantiate` 只接收明确提供的 region 节点列表，不对原型做推断。要求 region 名称完整一致；可以提供空列表，后续结构 QA 决定内容是否遗漏。模板保留全部输入，不重排业务项。

| Pattern | region 顺序与结构 |
| --- | --- |
| list-page | header、query（24 Grid）、toolbar（HorizontalStack）、table、pagination |
| detail-page | header、summary、detail |
| form-page | header、form（24 Grid）、actions（HorizontalStack） |
| dashboard-basic | header、metrics（24 Grid）、content |
| sidebar-content | sidebar（固定 size.sidebar） + content（Fill）横向排列 |

模板使用 size.page、spacing.page、spacing.section 等 Token，不提供未登记组件、图标或图片。

## 执行与产物

```powershell
.\.venv\Scripts\python.exe -X utf8 -m validators.layout examples/user-management.layout-tree.json --output-dir artifacts/task-004
```

保存 layout_skeleton.json 和 layout_qa_report.json。成功返回 0，错误返回 1。消费端必须检查 status=PASS；PASS 只表示已提供的树与测量通过本任务布局检查，不能标记最终设计或 V0.1 Ready。
