# TASK-019 — 双平台冻结表格组件准入 PASS

2026-10-10。两列两行与四列四行官方 Table 正文已完成原生制造、完整保真、真实实例、视觉复核及组件库 0.2.1 的显式发布。此任务不生成新的业务页面，不扩展任意数据改写。旧 V0.1 程序、默认组件库和首次端到端版本锁保留。

| 项目 | 两列两行 | 四列四行 |
| --- | --- | --- |
| 来源尺寸 | 720×96 | 960×192 |
| 每个平台主组件／实例节点数 | 14／14 | 42／42 |
| Figma 主组件 | 69:4 | 69:18 |
| Figma 真实实例 | 76:2 | 76:16 |
| Figma 完整保真 | PASS；2139 个栅格差异 | PASS；3631 个栅格差异 |
| Penpot 完整保真 | PASS；2182 个栅格差异 | PASS；3614 个栅格差异 |
| 独立边缘带外／文字范围外差异 | 两平台均 0／0 | 两平台均 0／0 |
| 实例完整原生 PNG | 与主组件逐字节相同 | 与主组件逐字节相同 |
| 全节点内容／样式／相对几何及真实关联 | 两平台 PASS | 两平台 PASS |

Penpot 主组件、实例及 Component ID 在 `adapters/penpot/metadata/configurable-table-native/*instance-after-placement.json`。Figma 的只读分片重新组装后必须通过整体 SHA256；全部实际创建节点、源主组件未变、主组件／实例读回、双次稳定 PNG 与传输超限失败均保存。Penpot 的初始位置重叠和一次 HTTP500导出超时保留；仅移动实例，最终分别在640位置，主组件及所有文字样式不变。浏览器证据为 instances-browser-review.png。

## 字体与几何证据

Source 仍绑定 TASK-018 两份请求、原始官方提取程序、CSS、IR、像素及逐单元格 baseline。补回官方容器白底，保留旧漏白底的失败报告。0.2.1仅用正面积交集分类小数文字矩形所覆盖的像素；不改源矩形、边缘带或字形保留门。旧0.2.0程序恢复原字节，新政策在独立 Adapter 模块中。

Arial 使用用户已批准的 TASK-019_ARIAL_ENCODING_DECISION.md；源字体、FreeType2.13.2实际加载 DLL 路径与 SHA、包装器、程序及完整捕获均锁定。20个单字形、6个实际 Arial 完整字符串逐点有向编码精确一致；固定1024ppem字宽和自动框取整、独立15px基线严格核对。苹方全部单元格使用原CFF精确编码和独立16px基线。源字体在真实官方浏览器中显式绑定后的截图与官方来源逐字节相同，临时状态全部恢复。

Penpot 完整原生 SVG 在源字体容器下逐像素等于官方；实际PDF的 Arial TrueType 子集坐标、指标、指令及 hint 表精确匹配，苹方 Type3字形及全部实际PDF基线通过。Figma 全部实际 Text 轮廓、节点字形位置、字体、字号、行高、自动尺寸、颜色、父子关联、边框、裁剪与完整SVG绑定通过。最终仍以未经处理的原生 PNG 验收，不用向量图代替。

## 显式组件库版本

发布目录 `releases/component-library-0.2.1/` 包含平台无关的版本化Core Registry、原schema、catalog、正式完整报告、四份原生PNG及哈希manifest。平台引用和原生凭证只保存在两个Adapter的 `metadata/component-library-0.2.1/`。新中立 Registry 仅接受这两份请求的0.2.1政策，保持旧0.2.0规则；`load('0.2.1')` 逐文件检查后返回 Registry 和双平台绑定。没有覆盖旧默认库或自动升级旧任务。

最终Registry指纹：b88aa1d02345d057956bfa6f6632cbcfb87047e7851aeaacbea311ff39a09356。初次未提交的发布候选在补强实际DLL加载检查后归档到 ignored artifacts/task-019/prepublication-v1，新完整准入重新执行，旧候选没有当作已发布版本覆盖。最后版本说明见发布目录README。

两份冻结实例在合成UI-IR的双平台预检中通过，明确 nativeExecution=NOT_RUN；这仅验证新Registry与Adapter入口桥接，不宣称新业务页面已验收。Penpot 使用独立 configurable_table_compiler 和基于实际Registry类型的凭证检查；原执行payload ABI不变。所有新字段／数据变化仍需新来源与完整验收，不能改变这两份组件文字。

## 检查

- 全项目413项Python PASS（245.989秒），108项Node PASS（18497.58毫秒）。
- 随后新增显式版本的双平台入口检查及历史Release Gate，6项PASS（17.120秒）。
- 最后补强实际加载DLL身份并重新生成全部准入，再跑Arial、新库、双平台完整门／真实实例、历史Release Gate及Core架构，26项PASS（39.838秒）。没有把旧403／405的失败运行宣称为全套通过。
- 拒绝字体文件、库身份、字符、轮廓控制点、baseline、字宽、颜色、内容、几何、缺失／重复捕获、假实例关联、节点／截图变化、未批准Table政策扩展及版本混用。实例创建和导出失败保留实际账本与回执。
- 四份完整原生PNG实际视觉检查PASS，行／列／完整文字／分隔线可见；Penpot浏览器显示分离排列的主组件与关联复制实例。

正式门证据在 release/evidence 与各Adapter原始metadata。Source、字体、原生PNG、独立向量和实际读取均有字节绑定；Source图片未覆盖，字体文件未提交。
