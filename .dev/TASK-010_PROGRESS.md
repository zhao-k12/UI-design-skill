# TASK-010 — Penpot Adapter 进展

日期：2026-10-08。状态：PASS；完整实际验收见文末与 TASK-010_ACCEPTANCE.md。早期记录保留。

已完成 TASK-009：`f749fb5`。本任务继续使用相同 UI-IR，规范化 SHA-256 为 `94fa6d9483f78754913cf5089a3c1d70887debdd953edd9f0bd14208e4b155d1`。Core、Token、逻辑 Registry 与 Figma 原生输出保持原值。

## 已实现

独立 Penpot 编译器和命令入口；原生 Board/Flex、可编辑 Text、真实 LibraryComponent.instance 调用；严格文件/字体/主组件/尺寸预检；已有页面防重建；部分失败精确 ledger；单独只读 discovery、属性 capture 与原生 PNG 导出。Penpot 组件绑定要求自身的完整原生 capture 和版本化保真报告，不能只使用 Figma 的 PASS。

API 依据为官方文档及官方源码固定提交 `5baffdc213f0deaaeb318e97a41d611ac0656a94`。下载类型文件 SHA-256：`42d08b7f862d1b3ff9a8d0b5449d124af7939cff81005c492605ecd4b2969fb6`。此项仅为开发参考，不证明目标 Penpot host 的版本。

## 本地验证

- Python 全套 241 项 PASS（包含新增 6 项）；之后编译器映射参数类型检查调整已再次运行相关测试。
- Node 全套 60 项 PASS；其后新增 4 项，Penpot 共 9 项再次全部 PASS。64 个测试均已覆盖，新增检查包括 Flex/Grid 原生属性设置及 capture 范围/图像大小拒绝。
- 固定 TASK-009 输入保持相同规范化指纹；无实际目标文件时 CLI 返回 FAIL / missing_target_file / nativeExecution NOT_RUN，plan=null，无执行脚本。
- 本地运行中使用的 API 替身不构成 Penpot 设计、截图或组件保真证据。

## 真实验收待办

当前未发现可用 Penpot 连接，浏览器库存没有已登录 Penpot 页面。已异步询问用户使用官方云端还是自建站点，以及目标文件链接。

收到目标后必须实际发现字体与文件身份，按官方 Component IR 建立四类组件并通过 AD-017 原生保真，导入官方 Remix SVG 为真实图标组件，登记 Penpot 原生引用。之后执行完全相同 UI-IR，独立读取节点、字体、布局和主组件关系，检查真实可编辑内容及 1 倍原生 PNG，与 Figma 验收页核对结构。全部通过才完成 TASK-010 并采用 BUILD_PLAN 的里程碑提交名称。当前提交仅保存基础实现，不进入 TASK-011。

## 第二次推进（2026-10-07）

新增独立原生结构 QA 与只读恢复检查。capture 现在保存完整原生父子树、子节点顺序和文件 revision；导出期间文件变化则拒绝证据。结构 QA 校验输入指纹、文件/页面/根节点身份、完整创建记录、节点顺序、Grid 包装关系、尺寸/模式、字体/内容/增长模式、颜色/边框/圆角/透明度、组件复制关系及可编辑文字、原生 PNG 格式与尺寸。结构成功只返回 REVIEW / structuralStatus PASS，finalAcceptance 与 fidelityGate 仍 NOT_RUN。

恢复检查仅读取精确部分失败记录，显示仍存在、已缺失和未登记子节点，不自动删除或重复构建。部分失败执行结果补全 fileReference、scope 和 adapterVersion，供恢复验证。

验证：25 项相关 Python 测试 PASS（11 项结构 QA、6 项编译器、8 项架构）；13 项 Penpot Node 测试 PASS。测试使用明确标记的合成结构/API 替身，新增正反例不能作为 Penpot 实际平台证据。复查未发现已登录 Penpot 会话，工具列表仍无 Penpot 能力。随后已打开官方云端 https://design.penpot.app，实际页面停在 /#/auth/login（登录我的账号），确认需要用户登录并提供验收文件。该浏览器页保留供后续接入；没有创建账号或文件。真实验收继续 NOT_RUN。未进入 TASK-011。

## 第三次推进：真实工作区接入（2026-10-07）

用户已在内置浏览器登录。实际团队 HeinQi（45145cff-4092-8110-8008-acf328e8a85a）；新建并命名 `UI Design Skill — TASK-010 验收`，file-id 91396aad-60c8-808b-8008-c0885ca79899。UI 可见身份记录保存在 adapters/penpot/metadata/file-identity.json，不作为 native API 或保真证据。

已实现项目自建只读诊断 host，服务仅绑定 127.0.0.1 的浏览器安全高端口，静态文件白名单，无通用代码执行/文件读写端点。插件仅含 content:read/library:read，代码严格限定该验收文件；结果仅保存项目 artifacts。真实 HTTP 验证只读 manifest、未知端点 404、外部 Origin 403；2 项 worker 测试验证跨文件读取及未知消息均停止，25 项相关 Python 测试 PASS。

Penpot 实际插件窗口提示授权可读取用户有权访问的文件内容及库/素材。按浏览器授权规则已询问用户批准，当前停在“允许”之前。权限窗口截图保存至 artifacts/task-010/plugin-permission.jpg。未点击允许、未执行原生字体发现、未生成组件或列表页，真实验收仍 NOT_RUN；未进入 TASK-011。

## 只读原生成功、字体安装与候选准备（2026-10-07）

用户分别明确批准只读诊断插件和两份字体上传。实际 Plugin API 读取成功，原始 receipts 位于 artifacts/task-010/live-host-1/discovery-1.json 至 discovery-3.json。初始 1911 字体系列、0 本地组件；上传后团队界面显示 PingFang SC Regular/Ionicons Regular 已安装，刷新当前文件再读取获得 1913 系列。两份源文件 SHA-256 与 TASK-009 完全一致：0934ea94dea57d9ec12a401f44ad28b98c96f5ee9917df920279f58024de523a / 13d29fa1b804cd295603d17a7c9296c425af2724feaac7ce621f7cad43d8a31d。实际字体发现（不等于字形保真）保存至 metadata/host-discovery-requirements.json 和 metadata/font-bindings.json；上传截图 artifacts/task-010/uploaded-fonts.jpg。

固定 TASK-009 UI-IR 在实际文件和实际字体绑定下预检：FAIL，6 项缺失仅为 4 个原生组件、2 个原生图标。未改变 UI-IR 或 Core；该检查不是原生设计执行。

首个 Button 候选方案已准备，source Component IR canonical SHA 66d8984b25e8e3e080e864396eaf25f168fd2cf9395a6111628ed9ca7036ed4f。candidate 编译器、原生建立和独立 capture 模块不使用 Figma 基线；首次候选只使用官方源行框，baselineCalibration NOT_RUN。宿主拒绝被修改的源计划、跨文件、缺失字体、重复候选和未知消息。用户批准原生写入后才调用 createBoard/Text/Library.createComponent；此时仍不准入正式 Registry。方案详见 TASK-010_BUTTON_CANDIDATE_REVIEW.md。

写入插件实际权限窗口提示内容/库写入，已发出限定该独立验收文件的授权问题，尚未点击允许。权限截图 artifacts/task-010/native-write-permission.jpg。当前只读服务器 127.0.0.1:62410，候选服务器 127.0.0.1:57831（live-candidate-host-2）留作接续；它们只绑定本机回环。28 项相关 Python / 17 项 Node 检查 PASS，包含源计划篡改拒绝。原生候选建立、基线与组件保真、真实列表页均 NOT_RUN；未进入 TASK-011。

## 原生 Button 建立与实际失败检查（2026-10-07）

用户在原生写入批准请求后指示“继续开发”，按该上下文继续指定文件的候选建立。实际 Penpot 2.18.3 创建了一个 Library 主组件，60×32，含可编辑“查询”文字；没有注册生产组件。组件 ID 10f3de97-3a09-806f-8008-c0aff4ac5af0，主画板 ID 10f3de97-3a09-806f-8008-c0aff4723ada。已修正后续构建名称重复和重复创建保护。

实际导出 PNG/SVG、字体 CSS、独立文字转路径和创建记录完整保存于 adapters/penpot/metadata/button-native-v1。原生 SVG 的 @font-face 指向空 assets/by-id/；公开 generateFontFaces 返回同样缺失地址。独立诊断文字复制后 flatten 只返回 M400,80L428,80L428,101L400,101L400,80 的文字框矩形，原始可编辑文字未改动。原始回执的 OBSERVED 不代表字形证据，新的独立诊断报告明确 FAIL；后续探针遇到该矩形返回 UNSUPPORTED。真实 PNG 文字包围盒相对官方来源出现水平/垂直差异，未用猜测位移修正，也未复用 Figma 字形或基线证明。

官方 .penpot 文件下载可用，但不含字体字节；已观察资源无法取得，公共请求与浏览器链接返回 HTTP 403，不提取登录凭据或绕过访问限制。当前字体字形绑定、基线和完整保真仍未证明，TASK-010 未通过，Registry Penpot bindings 保持为空。下一步需解决当前原生导出字体资源及字形证据能力，再校准与验收；不进入 TASK-011。

验证：31 项相关 Python、18 项 Node 测试 PASS，其中新增空字体地址、矩形伪字形、错误文字引用和不完整证据不得准入反例。测试只验证检查行为，不构成平台 PASS。实际工作区截图 artifacts/task-010/button-native-v1/workspace.jpg。

## TASK-010 字体回退修复与原生 PDF 字形证据（2026-10-07）

发现明确根因：原生 PDF 的实际嵌入字体为 WenQuanYiZenHei，而非界面显示的 PingFang SC。官方字体管理页下载了团队原始苹方，其 SHA-256 与 TASK-009 锁定文件完全一致。对照 Penpot 2.18.3 官方源码 ff7a66f51938b2293260ea27a64e2c4e0833b5e3，custom font CSS 使用 WOFF1 资源，原上传变体对应地址为空。重新选择 UI 家族/Regular 仍未修复。

在已有两份字体、同一 HeinQi 团队的上传授权范围内补传 WOFF 容器，保留旧变体。font_container.py 对原始文件 SHA 和解压后的全部字体表严格检查：苹方17表、Ionicons11表一致，仅容器 head.checkSumAdjustment 字段归零比较；字形、度量、名称、时间戳及 hinting 均未修改。表检查不等于 native 保真。

刷新实际文件后，native generateFontFaces/SVG 出现有效 WOFF 地址，native PDF Type3 FontDescriptor 两处均为 PingFangSC-Regular/400。PDF CharProcs 保存真正字形路径，查询分别46/52条完整命令，反映已声明 FontMatrix 的 y 方向后与锁定字体的有序完整轮廓、advance/font identity 精确相等。独立 glyph_font_unit 检查 PASS；PDF 文本矩阵实际基线20.5（不是复制 Figma baseline）。PDF矩阵序列化0.0010000001、第二字符位移13.999939仍保留，不能冒充整个缩放/位置严格证明。原生 PNG60×32，相对来源281像素差异；完整八项 production proof、SVG浏览器重现和 PNG边缘验证尚未完成。TASK-010与组件准入仍未通过，生产Registry绑定保持为空，不进入TASK-011。

只读 capture 新增实际 PDF 导出，PDF字体观察兼容原生Type3字形流；未知字形路径算子/偶奇填充/不完整轮廓/不支持矩阵/错误字体/改变轮廓或advance均拒绝。35项相关Python、19项Node检查PASS（新增重复容器同ID去重/不同ID拒绝测试）。前后原始回执/PDF/PNG/SVG/字体表证明/字形比较/修复报告均保存至 adapters/penpot/metadata/button-font-repair；真实上传与画板截图保存至 artifacts/task-010/font-repair。当前下一步为将上述独立原生证据纳入完整Button保真证明并验证像素边缘，不应重新处理已解决的空地址/回退问题。

## TASK-010 首个 Penpot 组件正式准入（2026-10-07）

Button 的完整 AD-017 / 0.2.0 保真 PASS，已通过独立 Penpot 凭据校验并登记原生组件 10f3de97-3a09-806f-8008-c0aff4ac5af0。逻辑 Registry/Core/UI-IR/Figma 引用未修改；Penpot component-bindings.json 指向真实组件，native-fidelity.json 保存自己的完整原生 capture、proofBundle 与 Gate 报告，不用 Figma PASS 替代平台证据。

原有同色 inner stroke 与填充重复绘制圆角；仅合并填充后仍有20个 SVG圆角差异。根据锁定 CSS 的1px内侧边框，建立真实原生背景 Rectangle：x/y偏移0.5，59×31，radius3.5，1px center stroke；外边界严格60×32/radius4。不是按像素猜测移动或修改来源。可编辑文字位置/字体保持原样，主组件当前3个原生节点。新候选构建也采用此来源几何。实际主SVG浏览器重现与来源 PNG逐字节相同（SHA377b2ea174242eaf9c271553d854926c89782a517cd6437d0c4e59f8926972f4），三个官方来源样例/环境重新提取一致。

完整原生属性包含可见/隐藏、旋转/翻转、透明度、混合模式、阴影/模糊与文字设置，导出前后快照及revision均稳定。实际PDF Type3全字形轮廓与锁定苹方完全一致；字体大小和位置另由原生SVG的明确14px/textLength28、源映射节点盒和整SVG零差异绑定，不把PDF浮点序列化误当精确SVG坐标。PDF实际baseline20.5与独立官方浏览器baseline证据严格对应。八项证明全部PASS。

原始native PNG保留不变；白底比较图只做有记录的alpha合成，无crop/resize/位移。279个差异像素全部位于独立向量边缘带与允许文字/圆角区域；查/询逐字保留比例0.7978895743 / 0.6923480673，通过已有规则。Penpot admission额外核验原始PNG字节、规范白底比较PNG、完整proofBundle哈希和Gate绑定。改变字体/位置/圆角/效果/透明填充/梯度/PNG哈希/缺失完整bundle均拒绝。

导出服务两次500超时已保留。capture按格式分别保存成功与失败，部分格式失败只标PARTIAL，禁止准入。后续完整capture成功；独立重复capture的PNG和节点逐字节一致，但文字单独SVG超时，因此重复证据只证明PNG/节点稳定，保留completeRepeatCapture=false，不冒充第二份完整证据。准入基于第一份完整原生证据与独立证明。所有原始及派生材料位于 adapters/penpot/metadata/button-admitted。

验证：38项相关Python与21项Node PASS；固定TASK-009 UI-IR预检FAIL仅剩5项missing（Input/Select/Table及2个官方图标），plan=null/nativeExecution NOT_RUN。输入规范SHA仍94fa6d9483f78754913cf5089a3c1d70887debdd953edd9f0bd14208e4b155d1。TASK-010整体未通过，未进入TASK-011。下一步建立剩余官方组件/图标并分别实际保真，再执行相同固定列表页及双平台最终QA。

## TASK-010 Input 原生保真准入（2026-10-07）

建立并正式登记真实 Input Library 主组件 b17404b9-592b-8074-8008-c0cd36551084，主画板 b17404b9-592b-8074-8008-c0cd362de6d1。240×32、白色填充、#dcdee2 的1px来源边框中线、可编辑“请输入姓名”苹方14/400。初次导出背景遮住文字；修正实际图层顺序并给后续构建加入 setParentIndex(0)，失败回执/初次截图保留于 input-native-v1/initial-capture.json，不用于正式准入。恢复过程曾因 native 名称斜杠空格格式化被守卫拒绝，修正只规范名称分隔空格，拒绝回执保留。

最终独立 CAPTURED 包含完整 PNG/SVG/文字SVG/PDF/节点属性，前后属性及revision稳定。原生SVG在同版本锁定字体下重现与官方 Input PNG逐字节一致，SHA3c940cc44ef9cd1048a3ca8fcae8366b30eb22fc4866bbb8a75de3186d5b9855；三份来源/环境重新提取一致。独立 Input probe 文件保留 Button 原探针不变，避免改变既有证据脚本哈希。

PDF 实际基线21与独立浏览器来源基线21一致。五字完整轮廓/advance/font identity PASS；PDF ToUnicode 将“入”记录为康熙部首“⼊”，锁定来源 cmap 证明两者映射同一字形，证据同时保留原生 Unicode 与别名标记，仅用于字形身份，不替代实际可编辑内容检查。新增错误别名拒绝检查。PNG保留原始字节，比较图仅白底alpha合成；684像素差异、0在边缘带外、0在允许区域外，五字覆盖保留率0.6773～0.7589，八项完整证明与共享 Gate0.2.0全部PASS。独立 Penpot receipt 校验实际PNG/比较图/全proofBundle/report/native绑定后登记，Core/逻辑Registry/固定UI-IR/Figma证据未改。

验证39项相关Python、23项Node PASS，新增错误占位内容/字体/位置/背景图层顺序/文字梯度/缺失proof/PNG指纹不得准入。固定列表页预检仍FAIL，仅剩4项missing：Select、Table、2个官方图标；plan=null/nativeExecution NOT_RUN。实际截图 artifacts/task-010/input-admitted-workspace.jpg。TASK-010整体尚未完成，下一步 Select 原生候选与实际保真，再完成剩余资源和固定列表页；未进入TASK-011。

## TASK-010 Select 原生保真准入（2026-10-07）

正式登记 Select Library 主组件 b17404b9-592b-8074-8008-c0d00dc30929，主画板 b17404b9-592b-8074-8008-c0d00d917931。官方闭合选中态“启用”、真实 Ionicons U+F116 下拉箭头均为原生可编辑文字；240×32背景按来源1px边框中线建立，隐藏下拉列表不进入静态主组件。构建前校验两种精确字体、目标文件和重复主组件；源计划完全绑定已准入官方 IR，未改变 Core/逻辑 Registry/UI-IR/Figma 证据。

实际完整 capture 包含 PNG/主SVG/文字SVG/箭头SVG/PDF、两份font-face和全节点属性，导出前后属性/revision稳定。主SVG在两份锁定无损WOFF下浏览器重现与官方Select PNG逐字节一致（SHA a5b75597a1079927013cfd47f77fabad43779ddf2455c8027863736be196f12f），三份官方参考/环境重新提取一致。原生 PDF 中文字体 Type3 轮廓/advance/identity精确一致；Ionicons 使用 Type0/Identity-H/CIDFontType2/Identity 映射与实际嵌入836字节TrueType子集。新增独立核验器检查 CMap U+F116/CID26、源字体SHA、1024 unitsPerEm、PSname/weight、完整有序轮廓、advance/left-bearing及hint指令，全部相等。不将整字体子集与完整来源文件当作逐字节相同。

PDF 实际中文baseline21、箭头baseline22，与官方独立浏览器测量分别一致；原生SVG位置/字宽也独立验证。原始PNG保留，仅白底alpha合成；302像素差异，0在边缘带外、0在允许区域外，启/用/箭头覆盖保留率0.9114/0.8524/0.9703。八项完整证明及共享Gate0.2.0 PASS，独立Penpot receipt验证全bundle/原生PNG/比较图/报告绑定后准入。证据保存 adapters/penpot/metadata/select-native-v1；工作区截图 artifacts/task-010/select-admitted-workspace.jpg。只支持已观察的单字形 Identity-H 子集，其它字体映射/范围拒绝；不声称通用PDF字体支持。

44项相关Python和24项Node检查PASS，覆盖外文件/重复主组件/箭头缺字或错字体/位置/父级/隐藏/透明/梯度/错误嵌入字体与映射/缺失全凭据等拒绝。诊断依赖pypdf通过追加bundled runtime路径运行，保留项目Python/Pillow优先级；最初PYTHONPATH覆盖造成Pillow二进制版本冲突，已改为追加路径并完整复验。固定验收UI-IR预检仍FAIL，仅剩3项missing：Table及两个官方图标，plan=null/nativeExecution NOT_RUN。TASK-010整体未完成，下一步Table与图标原生保真，再生成同一固定列表页和最终双平台QA；未进入TASK-011。

## TASK-010 Table 原生保真准入（2026-10-07）

正式登记真实 Table 主组件 6d6e57fb-4a0a-8065-8008-c0f928688eff，主画板 6d6e57fb-4a0a-8065-8008-c0f92704d041。共26个真实节点，保留3行/9单元格/9可编辑文字、3条行分隔线及独立底部::before。外框1392×144并裁剪，内部行宽1393；列宽464.328125/464.328125/464.34375严格来源不均分。源计划绑定官方IR/截图/观察/字体/源码CSS，未复用Figma原生基线或平台ID。

完整独立capture含原始PNG/SVG/首个文字SVG/PDF/全节点属性与字体CSS，前后属性/revision稳定。Table专用SVG浏览器探针重新提取同一官方表格/环境；原生主SVG重现PNG与官方参考逐字节相同，SHA a2730f5b7f2e386d5a7ff1a9779841d73c359b2e90009aa80a2e5f1e1e99b02a。九个文字位置/字宽逐项严格绑定原生属性和SVG。实际PDF基线28/76/124分别一致，x482.328125在PDF序列化为482.32813：仅检查实际五位小数half-up格式，完整精确x另外由原生节点和全SVG零差异证明，不声称PDF浮点x精确等于源坐标。

PDF Type3在部分资源中含2或3个bfchar映射，新增严格单块多条目解析；未知范围/错误计数/重复code或Unicode拒绝。16个不同汉字的完整有序轮廓、advance、字体身份与锁定苹方相等；“用”存在来源cmap验证过的康熙部首Unicode别名，实际可编辑内容另行严格校验。原始PNG保留，仅白底alpha合成；2354差异像素，0在边缘带外、0在允许区域外，非文字区域与来源相同。九文字覆盖检查及八项完整证明、共享Gate0.2.0 PASS，独立Penpot receipt校验全bundle/nativePNG/比较图/report绑定后登记。全部证据 adapters/penpot/metadata/table-native-v1；截图 artifacts/task-010/table-admitted-workspace.jpg。

登记前49项相关Python、26项Node PASS。登记后17项Adapter/QA检查最初1项失败：旧测试从真实metadata推断必须有missing_component_reference，四类组件全部登记后该假设失效。已改为显式构造空绑定测试缺失资源拒绝，不改生产绑定或降低断言；49项相关Python完整复验PASS。新增错误列宽/内容/字体/位置/根裁剪/边框/梯度/父级、缺失字体、外文件、重复或外来文本清单和PDF映射拒绝。固定UI-IR预检仍FAIL，仅剩两个missing_icon，plan=null/nativeExecution NOT_RUN。四类组件全部真实Penpot保真PASS，TASK-010整体尚未通过；下一步两个官方Remix图标、同一固定列表页和最终双平台结构/视觉QA。Core/UI-IR/逻辑Registry/Figma证据未修改，未进入TASK-011。


## TASK-010 官方图标：批准编码规则与完整原生导出（2026-10-07）

用户明确批准 TASK-010_ICON_PRECISION_DECISION.md 的来源约束 Float32 规则，已记录为 APPROVED。仅限两份官方 Remix SVG SHA；有序命令/闭合/轮廓/坐标须精确等于来源 Float32 编码，无容差阈值。新增版本化 geometry subcheck 0.1.0，保留 sourceCoordinatesExact=false 及原始差值，不将批准当作资源准入。

两份官方字节经公共 createShapeFromSvg 建立真实 LibraryComponent。设置组件6d6e57fb-4a0a-8065-8008-c0fc685ca781，下载组件6d6e57fb-4a0a-8065-8008-c0fc6866e456。首次远处放置产生额外舍入，已在原点恢复来源路径；后续构建也使用原点和显式包装层opacity1。包装层实际API opacity初值null，严格内容组检查拒绝；按来源显式设置1后重新capture，没有将null直接当作通过。

保留最初三次下载PNG超时、内容组SVG超时及一次设置主PNG超时。最终latest-main-capture.json的两个主组件均CAPTURED，完整原生PNG/SVG无exportIssues，前后属性/revision稳定。原生内容组PNG与最终主PNG逐字节一致，但内容组capture因SVG超时仍PARTIAL，不冒充完整主证据。独立SVG探针3绑定最终capture SHA a23fc55c57c21c99722db31dcfe84a7f9641ac5660fd59e5d9344e714ed8b84a；两图标源/原生SVG重现PNG逐字节一致，completeNativeCapture=true。所有证据保存adapters/penpot/metadata/icons-native-v1，截图artifacts/task-010/icons-complete-capture-workspace.png。

新增native_icon_evidence子检查严格验证原始receipt字节、上下文/版本/来源SHA、24×24完整PNG、主导出scope、全节点清单/父级/可见性/样式/效果/填充、原生d和SVG路径一致、精确来源编码及绑定SVG重现。完整原生证据子检查PASS，admissionEligible仍false；未将此子检查冒充完整图标Gate。原生PNG仅白底alpha合成对照，设置138像素、下载42像素不同，记录为OBSERVED/nativePngVisualAcceptance NOT_RUN，无新增阈值或栅格豁免。图标生产绑定仍未建立，固定列表页尚未执行；四类组件既有PASS、Core/UI-IR/逻辑Registry/Figma证据未改，未进入TASK-011。

验证55项相关Python、29项Node通过；覆盖外文件、修改SVG字节、未批准来源、错误坐标/轮廓、PARTIAL、修改PNG/来源/paint/parent/效果及内容组替代主scope的拒绝。下一步完成图标原生PNG视觉验证与完整准入，再执行相同固定列表页和真实实例/双平台最终QA。


## TASK-010 图标原生栅格规则边界（2026-10-07）

ARCHITECTURE_CONFLICT / PENDING_DECISION：现行AD-017允许文字与已证明圆角边缘差异；已批准图标提案只补充Float32编码，未明确授权图标原生PNG边缘差异。最新完整原生PNG对来源仍138/42像素不同，不能自行给图标套用文字/圆角Gate。影响仅两图标生产准入及依赖的固定列表页，四个组件PASS不受影响。建议见TASK-010_ICON_RASTER_DECISION.md；依赖工作停止，独立只读调查与反例检查已完成。

新增source/native/vector三份独立图片绑定的原生栅格诊断：原生SVG重现与来源PNG逐字节一致；138/42差异全部位于既有AD-017向量edge_band，带外0。全部有效native RGB严格黑色；两图标前景区域各2，包围盒均精确一致，前景/空白连通区域数量一致；设置图标部分空白区域包围盒不同已记录，不声称逐像素相等。独立内容组PNG与最终完整主PNG逐字节一致，节点/revision/SVG一致；内容组SVG超时仍PARTIAL，未冒充第二次完整capture。该分析不证明具体渲染器原因、不引入阈值、不修改原始PNG，也不构成Gate PASS。

完整逐像素记录native-raster-diagnostic.json、审查图raster-review.png位于adapters/penpot/metadata/icons-native-v1；图标仍未登记，列表页未执行，未进入TASK-011。待用户决定仅限两份来源锁定图标的边缘栅格规则扩展后，再实现完整准入并实际验收。


## TASK-010 最终验收 PASS（2026-10-08）

用户明确批准两份图标的证据约束边缘规则，决策已解除。图标正式准入绑定完整capture/来源/脚本/向量重现/原生PNG及重复证据，compiler拒绝只填平台ID或手工PASS字段。四类组件及两份图标均已正式登记。固定UI-IR规范SHA仍94fa6d9483f78754913cf5089a3c1d70887debdd953edd9f0bd14208e4b155d1。

实际Penpot页面6d6e57fb-4a0a-8065-8008-c10659a6d9f7，根6d6e57fb-4a0a-8065-8008-c1065a3d80c2。34逻辑节点、78创建节点、6真实实例；与Figma同一UI-IR的逻辑节点/文字/尺寸一致，19个原生布局容器的实际位置符合声明padding/gap/对齐。原生完整PNG1440×496，目视无缺失/重叠/裁剪。

首次结构失败保留：斜杠空格名称、反向原生堆叠顺序、默认opacity=null及496.0000000000001高度序列化。实际显式恢复来源opacity1，保留raw stack顺序并做可追溯布局顺序归一化；PNG尺寸复用既有结构数值相等检查，未改变图标几何规则。关联图标resetOverrides消除多次移动额外舍入，保持真实copy、不detach、不改来源路径；实例世界坐标逐点精确等于已验证主路径经过实际平移的Float32编码。

四类UI组件实例PNG与准入主PNG逐字节一致，Table九文字可编辑。两图标SVG重现与来源逐字节一致，实例原生差异137/42像素全部在验证边缘带内；带外0。导出500回执均保留，恢复只复用同revision、同全节点/主节点状态的成功格式，缺失格式重新实际导出，拒绝混合版本。最终六实例完整CAPTURED，根独立capture v0.1.1验证可见性/效果及稳定渲染状态。

完整证据、失败回执、原生PNG/SVG、审查及最终QA在adapters/penpot/metadata/list-acceptance，proof-manifest绑定源文件和证据字节。全套291项Python、87项Node PASS。TASK-010完成；未宣称完整V0.1 Ready。下一阶段TASK-011尚未实现。
