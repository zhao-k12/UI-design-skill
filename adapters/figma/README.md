# Figma Adapter 0.1.0 — TASK-009 固定列表页验收通过

compiler.py 校验 UI-IR、Token、正式组件准入和平台 Metadata 后生成中立数据的 Adapter 载荷。runtime.js 将载荷翻译为 Figma Plugin API；只在 Adapter 中保存平台引用，不改 Core/UI-IR。不做视觉调整或推测替代资源。

```powershell
.venv/Scripts/python.exe -X utf8 -m adapters.figma examples/adapter-fidelity-acceptance.ui-ir.json --file-reference 0vGWSRoLxBiVPXiZ8xJAX9 --font-bindings adapters/figma/metadata/font-bindings.json --icon-bindings adapters/figma/metadata/icon-bindings.json --output-dir artifacts/task-009/list-preflight
```

Button、Input、Select、Table 的四个静态来源变体已通过保真并登记；固定验收 UI-IR 的真实页面见 [Figma](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9?node-id=35-3)。它有六个实例，四个 UI 实例的实际 PNG 与准入主组件零差异。最终记录为 metadata/task009-final-qa.json，原生截图为 metadata/list-acceptance.png。

上述命令仅预检/生成 host 脚本，不连接 Figma。调用真实 host 必须使用 figma-use 指南并保存返回 ID。原始 examples/user-management.ui-ir.json 中还有 planned 组件和未支持的 props/slots，仍明确阻止执行。完整 Task-009 验收不等于任意页面或双平台 Release Gate 通过。

独立布局验收输入 examples/adapter-native-smoke.ui-ir.json 已通过实际执行：[Figma 验收文件](https://www.figma.com/design/0vGWSRoLxBiVPXiZ8xJAX9?node-id=7-2)。该输入明确包含通用 Frame/Text 与 IconInstance，没有冒充 Button/Input/Select/Table。原生结果为 1440×388，四列各 336，五个图标均为实例；34 个 UI-IR 节点的记录证据校验及组合截图检查通过。它不替代用户管理页面的组件保真验收。

## 确定性翻译

- Page → 原生 Page 加承载布局的 Auto Layout 根 Frame；保留 UI-IR ID→原生节点 ID 的独立映射。
- Frame/Section/Row/Column/Stack → 原生 Auto Layout Frame，使用 UI-IR 的 direction、gap、padding、wrap、alignment 和 Fixed/Fill/Hug。Section 是语义布局容器，不映射为不具备相同布局语义的画布 Section。
- Grid24 → 原生纵向行组、横向 Row 和固定宽度单元格包装；严格按 span、24 列、padding/gap 与已解析宽度计算。保留每个原始节点，辅助包装 ID 单独返回。不用绝对坐标复刻栅格。
- Text → 可编辑原生 Text。字体映射键为 `fontFamily:fontWeight`，值为实际发现的 `{family,style}`，可包含经发现/验证的 `variationSettings:{wght:...}`；不猜 style 名称或替换字重。Host 先确认字体/轴存在、await loadFontAsync，再编辑文字；宽度非 Hug 时使用 HEIGHT 文本重排。空文本尚未排版时 fontWeight 读数可能滞后，显式 wght 轴参与校验，并返回字体数据与字重读数；实际标题最终字重为 600。
- ComponentInstance/IconInstance → 已验证本文件 COMPONENT 的 createInstance；不绘制替代、不 detach。组件绑定必须匹配正式 Registry 及保真报告，图标绑定必须匹配官方 SVG、Scope、目标文件和 Registry 哈希。
- Color、Border、Radius、Shadow → 精确解析 Token 后翻译；色彩转 0–1，透明度放在正确的 Paint/Effect 字段。

预检遇到未知、不支持或缺失资源时给出明确诊断并取消整份执行计划。此初版不支持跨文件 import、无映射的 props/slots 注入、实例 Hug、图标非固定尺寸/任意改色、Image/Divider、无确定宽度的 Grid、垂直 Wrap 或不明确的 spacingToken 角色。不能以这些限制降低 TASK-009 的最终验收标准；应在继续开发时扩展明确映射并重新验证。

## Host 执行与恢复

一份脚本只处理一个 Page，一次 setCurrentPageAsync。在任何写入前校验全部字体和 COMPONENT 引用。Node.resize 在 sizing mode 设置之前执行，所有子节点先 parent 后设置 Fill/Hug；顶层根放在现有画布内容右侧。原始 gap/尺寸不被改变。

返回全部创建 ID、UI-IR 节点映射、辅助包装 ID、原生类型/尺寸、字体和 mainComponent 引用等证据。重复执行遇到已存在页面/输出会要求准确 ledger 与复验，不重复创建或删除已有工作。部分写入失败返回 FAIL 和已创建 ID，保留原生对象供精确恢复；不会把部分成功输出为 PASS。

生成脚本使用 JSON 序列化载荷，业务文字不会被拼成代码。每次运行根据 generated_scripts.json 只失效本 Adapter 记录且未被改动的旧脚本；用户修改或未登记文件保留并报告，不能自动覆盖。只有 preflight 和生成脚本 ledger 均 PASS，才能提交 host。

icon_library.js/icons.py 从校验过的原始 SVG 直接导入可编辑 Vector 并转为 COMPONENT；使用由 figma-generate-library 的 validateCreation.js 改编的异步验证。原生组件及矢量证据保存在 metadata/icon-import-evidence.json，映射为 icon-bindings.json。没有手画图标、从其他库兜底或为图标制作任意外观变体。

单元测试的 Plugin API 模型仅检验翻译与调用约束，不证明实际 Figma 支持或视觉结果。实际文件、Node ID、独立截图、失败/恢复记录和验证结果均已保存，详见 metadata/runtime-state.json、native-smoke-evidence.json 与 artifacts/task-009/native-smoke。一次真实字体检查失败后按精确 ledger ID 清理此次空节点并在原 Page 恢复，没有删除原生图标库。

完整 TASK-009 仍需 Fidelity Gate、props/slots 明确映射以及用户管理页面生成。用户上传的 PingFang SC Regular/Ionicons 已实际发现并加载；三个官方默认静态候选已有独立 capture，精确截图仍未通过，生产组件仍为 0 active。

## 带来源基线校准的 Button 候选

候选脚本准备命令 `python -X utf8 -m adapters.figma.candidates` 可显式附加 `--button-baseline-evidence adapters/figma/metadata`。该目录必须包含完整官方 baseline、修复后的实际 native outline、字体文件 identity 与组件执行 inventory 四份证据。准备器重新核对原 IR 哈希、来源截图/环境复现、字体轮廓/字体绑定与实际尺寸后生成 `button-static-baseline-v0.1.1`；缺失或改变的证据失败，不猜偏移。未提供该参数时保留历史未校准生成方式，不能称已对齐。

校准方式保留官方 source/0.0 span 的 Auto Layout 盒，并在盒内放置可编辑 Text。Host 先核对新 Text 实际尺寸和导出 SVG 与已验证字形完全相等，再按证实的 baseline 偏移放置；重复候选名称拒绝并保留精确创建 ledger。准备脚本不执行 host、不登记正式组件。真实候选 18:5 的基线为 20.5，原生 PNG 与先前单独修复的 12:4 完全一致；浏览器参考仍有 317 个差异像素。

## 渲染属性诊断

native_capture v0.1.1 增加实际混合模式、旋转、mask 和文字装饰/大小写/段落属性；旧 capture 保持历史版本，不补造缺失值。render_state_diagnostic.run 接受真实参考目录、官方补采报告、按逻辑 ID 指定的 immutable capture 目录与显式 file_reference，核对来源和 capture 身份后比较明确可表达的渲染状态。实际三个候选有 44 项属性一致，四个 Text 的 PASS_THROUGH 与 CSS normal 等价仍 REVIEW。报告见 metadata/observed-render-state-report.json；此诊断不替代完整样式归一化或 Fidelity Gate，旋转、mask 等采集值仍须独立规则核对。

blend_mode_probe 对明确的现有 Text inventory 临时切换 PASS_THROUGH→NORMAL，并 finally 恢复；这是有 mutation ledger 的可恢复实验，不是只读 capture。三个阶段分别读取实际布局/字体/样式并导出 PNG。blend_mode_diagnostic 核对基准 capture 身份/完整性、before 与保存证据、仅 blendMode 改变、观察状态与像素恢复，独立解码 PNG 后严格计算差异。metadata/blend-mode-pixel-report.json 的三个实际组件在 NORMAL 下均 0 changed pixels，恢复后也为 0；仅排除当前内容/背景下的混合模式像素影响，不宣称一般 CSS 等价，因此原 render-state REVIEW 和精确 Fidelity FAIL 保留。

font_outline_comparison 的 nonzeroWinding 比较保留轮廓方向，只归一化公共平移、轮廓顺序和循环起点；允许所有轮廓统一反向，拒绝凭无向几何相同推断单独翻转孔洞仍等价。实际“查询/请输入姓名/启用”均为全部轮廓反向，其路径在 nonzero 规则下的填充区域严格等价；Ionicons 微小坐标差保留 REVIEW。证据见 metadata/font-nonzero-winding-report.json。此结果不认证字体渲染器的填充执行、hinting 或像素相等。

font_hint_diagnostic 通过文件哈希绑定读取当前 glyph 的 CFF Type2 hint operators/展开子程序计数/显式 Private hint 参数，或 TrueType glyph instructions/global hint 表。它只检查来源数据，不运行字体 grid fitting；variable/CFF2/composite 未支持时明确拒绝。当前九个中文 glyph 无 stem/hintmask/subroutine operators，但 Private 中仍有 BlueValues、StdHW/StdVW、LanguageGroup；Ionicons 箭头 glyph instruction bytes 为 0。报告 metadata/font-hint-data-report.json 保持 REVIEW，不能据此排除自动 hinting 或认定剩余差异的引擎原因。

corner_raster_diagnostic 对已验证参考与 immutable native capture 的四个实际 radius 矩形按距外边缘的同一像素位置镜像统计，逐点保留原 RGBA/有符号差异，比较 source/native/delta 的严格四角对称性。只支持整数像素盒，不重采样或拟合圆弧。metadata/four-corner-raster-report.json 中参考四角均对称，native 四角并非严格对称；Button 每角 7 个差异像素，Input/Select 分别为 9/9/8/9。此观察不证明半径、位置或栅格引擎错误，不改变 radius 或 Gate。

capture_repeatability 验证 3–8 份 immutable capture 的 scope/file/component/logical/exporter 身份、不同 captureId 与文件完整性，分别比较原生属性哈希、PNG 字节和 RGBA 像素。测试 scope 显式为 test-fixture，不能作为 production 证据。2026-10-07 对三个现有候选各执行三次只读 host 导出，九份 capture 的各组件属性与 PNG 完全一致，也与原保存截图一致；metadata/native-export-repeatability-report.json 的 PASS 仅指当前观察中的稳定性，不是 Fidelity PASS，不认证未来导出恒定或差异原因。

native-svg-probe 将只读导出的完整原生 outlined SVG 放入同一官方浏览器 context 的独立 page，拒绝 scripts/event attrs/external resources/未知节点和变换，按实际 width/height/viewBox 渲染；原官方 DOM/参考不改，后续三张官方截图与环境严格复现。只接受新的空 artifacts 输出目录；失败保存 FAIL，样本 PNG immutable。metadata/native-svg-render-comparison.json 保存官方参考/native PNG/browser SVG 三方比较：317→288、675→640、311→275；browser SVG 圆角区域与官方参考均 0 差异，剩余在观察文字区域。它是栅格诊断样本，不是 Figma native PNG，不进入 Registry 或替代精确保真门。
