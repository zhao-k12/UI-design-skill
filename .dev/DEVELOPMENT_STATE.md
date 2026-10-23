# Development State — public edition

- TASK-139: 用户指出 TASK-138 入库单据页的其他一级菜单箭头遗漏、状态标签虽使用 Tag 但 `dot` 变体呈白底描边，与原型的填充标签类别不符。根因是原型初读将重复菜单汇总、只关注状态圆点，旧 QA 仅核组件存在与数量，且此前视觉 PASS 未逐项比较变体。已更新 HTML Skill：逐个可见实例记录前后图形、填充／描边、形状与控件角色；不看初稿从原图独立复扫；官方变体必须同时匹配显著特征。新增 `scripts/audit_prototype_observations.py` 作为新任务的来源与三态截图复核门，漏箭头、错填充及漏审项的 4 项测试 PASS；Skill 格式检查与 diff 检查 PASS。工具核结构化证据自洽，不能自动发现两次观察共同遗漏，仍须原图到整页截图的独立目视校对。本任务只调整 Skill 与新任务验收工具，未修改 TASK-138 页面；其旧视觉 PASS 不再视为完整验收。

- TASK-137: 用户指出 TASK-136 操作日志页遗漏顶栏搜索图标、消息／锁屏／管理图标，以及头像和用户下拉结构。根因是来源 Tree 只录入文字，现有自动 QA 仅核文字覆盖、组件数量及几何，误把非文字语义缺失判成整页 PASS。已更新 HTML Skill 与流程说明，新增逐区来源观察清单、纳入／排除／Review 判定、与 Tree 绑定的非文字和控件关系、四阶段复核及最终原型截图校对要求；疑似遗留元素不得静默删除。新增 [原型观察与验收](../docs/PROTOTYPE_OBSERVATION_QA.md)。本任务只调整 Skill 与审核契约，未修改 TASK-136 页面，也未新增自动图像识别；其原 PASS 仅覆盖旧检查项，完整复验仍未执行。

- TASK-135: 用户明确 AI 在分析原型后应先按语义提出初步布局，同时要求 Skill 加入官方整页组合参考。已更新主流程与 HTML 骨架审核：查官方组件文档／官方项目、记录参考适用性，再审整页截图的相邻区域边界、高度和背景关系；组件单项符合官方不再等同于整页布局合格。部门管理 TASK-134 页面此前三状态自动 PASS 未覆盖该审核，其顶栏与品牌区问题保留为已知 FAIL；本任务不修改页面或历史截图。新的整页流程复验尚 NOT_RUN。

- TASK-133: 根据用户讨论重订 HTML Skill：原型仅提取内容与关系；先核实锁定版 View UI Plus 来源并审核可见彩色组件骨架，再进入默认官方组件与最终内容；四类 QA 独立。新增 `docs/IVIEW_OFFICIAL_EVIDENCE.md`，禁止把截图测量、历史项目 Token 或自写 CSS 说成官方规范。导出器加入本地 `.ivu-*` 覆盖预检，历史 TASK-132 客户页 CSS 因覆盖官方组件被阻断并撤销其“规范交付”解释；主 HTML Adapter 移除显式 Inter 字体。旧 Core 的项目级几何和文字 Token 尚未逐项迁移核对，新的 iView 合规整页验收仍 NOT_RUN；历史三状态浏览器 PASS 只代表原检查项，不等于新规范 PASS。

- TASK-132: 用户提供客户管理截图。独立记录原图、内容 Tree、布局意图和分阶段审核；新增复杂客户列表 HTML 模式，使用官方 View UI Plus 控件和来源锁定 Remix 图标，保留侧栏、顶栏、五项筛选、六个工具栏操作、九列表格、十条可见重复记录及浮动标签。列表页按项目规则使用 24 px 内边距并填满可用表格宽度。`artifacts/task-132/customer-management/html-final-r2` 的同页骨架、组件、交付三状态浏览器 QA 全 PASS，最后截图已与原型人工校对；不增加未见记录、分页总数或业务交互。此模式只验收当前结构，非任意截图通用能力。

- TASK-131: 当前 Skill 主路线收敛为 HTML 单页交付。入口 `run_html_pipeline.py` 不再导入平台专用配置；新增 `prepare_html_workflow.py` 与 `run_html_checks.py`，独立执行来源 Tree、布局和 iView 规范门。当前 `SKILL.md` 与 `docs/HTML_WORKFLOW.md` 只描述 HTML 页面制作与三状态 QA。原用户管理原型按新入口从 Core 到单页重新跑通，见 `artifacts/task-131/html`，骨架、组件、交付均 PASS。历史任务资料保留作版本证据，不参与当前交付。

- TASK-128/129/130: 新增用户批准的 HTML 交付路线，复用 Tree、布局、iView 规范门和 UI-IR，以锁定的 View UI Plus 1.3.24 官方运行包/CSS 渲染。按用户最新决定只生成一个 `page.html`，同一页面依次显示彩色骨架、默认文案组件、最终内容；各状态独立浏览器 QA、截图与哈希均保存。1660px 用户管理原型单页实测见 `artifacts/task-130/single-page-r2`，合成原型“赵六”变体见 `artifacts/task-130/single-page-dynamic`，三状态均 PASS；变体不是用户审核的新原型。`html-official-runtime` Core 内容模式允许来源支持的文案与 Table 行内容变化；历史 Figma 原生内容模式不变。HTML→Figma 导入和更多组件类型的网页验收仍未执行。见 [TASK-128 架构决定](TASK-128_HTML_DELIVERY_DECISION.md) 和 [HTML 流程](../docs/HTML_WORKFLOW.md)。

- Implemented baseline: Skill V0.1，有限范围静态列表双平台验收完成；显式组件库版本包含0.2.1和0.3.0。
- Public snapshot: 完成基线 `6693e3e`，另加入公开文档和新的V0.2计划。
- Current development: V0.2 — PREPARATION；TASK-021/022/023 完成；TASK-024 默认字体绑定已实际观测（Figma Inter / Penpot sourcesanspro），两平台文字样张 PASS。TASK-025 来源审计、TASK-026 已批准改编政策和历史输入锁完成；TASK-027 Figma、TASK-028 Penpot Button 原生候选均已创建并来源对照；TASK-029 新 Penpot 文件输入锁迁移完成；TASK-030 字形与圆角诊断完成；TASK-031 当前 Button 配置的双平台新保真门 PASS；TASK-032 用户批准的固定内容范围约束及独立 V0.2 Registry/两端绑定已准入；TASK-033 默认字体 Input 候选来源审计完成；TASK-034 同一 Input 固定配置的双平台原生保真门 PASS；TASK-035 以固定占位、空值、240×32 准入独立 V0.2.1 Registry；TASK-036 默认字体 Select 双平台候选来源审计完成；TASK-037 同一 Select 固定配置的双平台原生保真门 PASS；TASK-038 以固定所选文字、值和 240×32 准入独立 V0.2.2 Registry；TASK-039 默认字体 Table 双平台固定三行候选来源审计完成；TASK-040 同一 Table 固定配置的双平台原生保真门 PASS；TASK-041 以固定列、九格数据和 1392×144 准入独立 V0.2.3 Registry；TASK-042 平台无关默认字体 Token 与双端页面 Adapter 预检 PASS；TASK-043 同一 UI-IR 双平台原生页面、独立读取及视觉验收 PASS，Penpot 组件主实例 ID 解析修正；TASK-044 完成完整流水线迁移就绪审计；TASK-045 新 V0.2.1 Token 的 1920 宽度、布局及双端 Adapter 预检 PASS；TASK-046 新 V0.2.2 Token 的最小 1080 高与长页静态增高、布局及双端 Adapter 预检 PASS；TASK-047 独立 V0.2 来源几何快照与准入哈希门 PASS；TASK-048 生产 CLI 显式 V0.2 Profile 与 V0.1 回归 PASS；TASK-049 当前 Penpot 文件两个 Remix 图标原生主组件和实例保真准入 PASS，结合新几何包迁移阻塞降至两项。B 阶段已完成六个限定组件准入，页面能力进行中。
- TASK-050: Figma 与 Penpot 默认字体自由文字各 12 项原生测量和独立读回 PASS；用户批准双端较大值包络，文字包络 PASS。
- TASK-051: V0.2 独立输入包、组合单元来源尺寸复算、1920×1080 Core 完整流水线与 Figma/Penpot Adapter 预检 PASS。
- TASK-052: 同一最终 UI-IR 的 Figma/Penpot 1920×1080 原生完整页面、独立结构/文字/实例读回、双端原生 PNG 和视觉验收 PASS；Penpot 末尾布局等待误报已限定修正。
- Current TASK-053: V0.2 发布就绪只读审计 PASS，结论 NOT_READY：18 类目标只准入 4 类固定配置，Adapter 运行时代码未纳入 Manifest 字节锁，新独立原型与全量 Release Gate 未验收；入口文档已按实际进展校正。架构冲突记录见 TASK-053。
- TASK-054: Tag 默认静态固定“启用”配置的官方来源锁、真实浏览器 DOM/样式/截图/字体和 Component IR 完整性 PASS；Figma/Penpot 默认字体改编与 Fidelity Gate 尚未执行，未准入 Registry，V0.2 仍 NOT_READY。
- TASK-055: Tag 固定“启用”配置的 Figma Inter／Penpot sourcesanspro 默认字体原生候选、组件实例、独立读回、重复 PNG/SVG 和来源对照审计 PASS（候选状态）；正式 Fidelity Gate 与 Registry 准入仍 NOT_RUN。
- TASK-056: Tag 固定“启用”配置的 Figma/Penpot 原生重复读回、双端正式 Fidelity Gate PASS，`admissionEligible=true`；Registry 准入尚未执行，V0.2 仍 NOT_READY。
- TASK-057: Tag 固定“启用”配置以独立 V0.2.4 Registry/双端原生绑定准入 PASS；旧快照与 V0.2 生产输入包不迁移，V0.2 整体仍 NOT_READY。
- TASK-058: Checkbox 固定“启用”选中态的官方源码/CSS、真实浏览器 Component IR、字体、截图和来源锁 PASS；双端默认字体候选、Fidelity Gate 与 Registry 准入均 NOT_RUN。
- TASK-059: Checkbox 固定选中态 Figma 默认 Inter 原生候选、主组件实例、独立读回和重复 PNG PASS（候选状态）。
- TASK-060: Checkbox 固定选中态 Penpot 默认 sourcesanspro 原生候选、主组件实例、独立读回、文件校验和重复 PNG PASS（候选状态）；正式 Gate 尚未执行。
- TASK-061: Checkbox 固定“启用”选中态的 Figma/Penpot 原生勾选标记及方框栅格位置修正、重复独立读回、双端正式 Fidelity Gate PASS，`admissionEligible=true`；Registry 准入尚未执行，V0.2 仍 NOT_READY。
- TASK-062: Checkbox 固定“启用”选中态以独立 V0.2.5 Registry/双端原生绑定准入 PASS；旧快照与 V0.2 生产输入包不迁移，V0.2 整体仍 NOT_READY。
- TASK-063: Radio 固定“启用”选中态的官方源码/CSS、真实浏览器 Component IR、字体、截图和来源锁 PASS；双端默认字体候选、Fidelity Gate 与 Registry 准入均 NOT_RUN。
- TASK-064: Radio 固定选中态 Figma Inter／Penpot sourcesanspro 原生主组件与实例、独立读回、重复 PNG/SVG 和来源对照审计 PASS（候选状态）；正式 Fidelity Gate 与 Registry 准入仍 NOT_RUN。
- TASK-065: Radio 固定“启用”选中态双端原生重复读回、圆形控件像素与双字完整性、正式 Fidelity Gate PASS，`admissionEligible=true`；Registry 准入尚未执行，V0.2 仍 NOT_READY。
- TASK-066: Radio 固定“启用”选中态以独立 V0.2.6 Registry/双端原生绑定准入 PASS；旧快照与 V0.2 生产输入包不迁移，V0.2 整体仍 NOT_READY。
- TASK-067: Switch 固定“开”选中态的官方源码/CSS、真实浏览器 Component IR、字体、截图和来源锁 PASS；双端默认字体候选、Fidelity Gate 与 Registry 准入均 NOT_RUN。
- TASK-068: Switch 固定选中态 Figma Inter／Penpot sourcesanspro 原生主组件与实例、独立读回、重复 PNG/SVG 和来源对照审计 PASS（候选状态）；正式 Fidelity Gate 与 Registry 准入仍 NOT_RUN。
- TASK-069: 用户决定暂缓连接不稳定的 Penpot 线，后续组件先走 Figma。Switch Figma 原生独立读回、重复导出、来源像素与字形质量核验 PASS；`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入均 DEFERRED，V0.2 仍 NOT_READY。
- TASK-070: Card 固定“用户信息 / 暂无内容”配置的官方源码/CSS、真实浏览器 Component IR、240×106 截图和来源锁 PASS；Figma 原生候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-071: Card 固定配置 Figma Inter 原生主组件与实例、来源变量绑定、独立读回、重复 PNG/SVG 及来源对照审计 PASS（候选状态）；单端独立 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-072: Card 固定配置 Figma 独立复读、重复导出、来源几何/非文字像素与字形完整性 QA PASS；`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-073: Pagination 固定三页配置的官方源码/CSS、真实浏览器 Component IR、400×32 截图和来源锁 PASS；Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-074: Pagination 固定三页 Figma Inter 原生主组件与实例、五格几何和变量、哈希锁定 Remix 左右箭头原生主组件/实例、独立读回与重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-075: Pagination 固定三页 Figma 独立复读、重复导出、数字和 Remix 图标可见性及来源非内容像素 QA PASS；`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-076: Tabs 固定“概览/详情”双标签配置的官方源码/CSS、真实浏览器 Component IR、320×73 截图和来源锁 PASS；Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-077: Tabs 固定双标签 Figma Inter 原生主组件/实例、标签栏与内容几何、变量绑定、独立读回及重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-078: Tabs 固定双标签 Figma 独立复读、重复导出、非文字区域 20,332 像素完全一致及完整字形 QA PASS；`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-079: Tree 固定展开三节点的官方源码/CSS、真实浏览器 Component IR、240×79 截图和来源锁 PASS；Component IR 契约补列 Tree 类型。Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-080: Tree 固定展开三节点 Figma Inter 原生主组件/实例、哈希锁定 Remix 展开箭头、文字颜色变量、独立读回和重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-081: Tree 固定展开三节点 Figma 独立复读、重复导出、非内容区域 11,862 像素完全一致及完整文字/展开箭头 QA PASS；`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-082: DatePicker 固定 `2024-01-01` 单日期的官方源码/CSS、真实浏览器 Component IR、211×32 截图和来源锁 PASS；Component IR 契约补列 DatePicker 类型。Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-083: DatePicker 固定单日期 Figma Inter 原生主组件/实例、哈希锁定 Remix 日历图标、来源颜色变量、独立读回和重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-084: DatePicker 固定单日期 Figma 独立复读、重复导出、背景和边框非内容区域仅四角抗锯齿 41 像素差异（最大通道差 4）、日期及日历图标完整性 QA PASS；`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-085: Form 固定“姓名 / 请输入姓名”单字段的官方源码/CSS、真实浏览器 Component IR、320×34 截图和来源锁 PASS；Component IR 契约补列 Form 类型。Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-086: Form 固定单字段 Figma Inter 原生主组件/实例、已准入 Input 原生实例复用、标签颜色变量、独立读回和重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-087: Form 固定单字段 Figma 独立复读、重复导出、非文字区域仅 Input 四角抗锯齿 41 像素差异（最大通道差 4）、标签和占位完整性 QA PASS；`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-088: Modal 固定“提示 / 操作已完成”打开态内容框的官方源码/CSS、真实浏览器 Component IR、320×104 截图和来源锁 PASS；Component IR 契约补列 Modal 类型。Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-089: Modal 固定通知内容框 Figma Inter 原生主组件/实例、来源颜色变量及阴影、独立读回和重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-090: Modal 固定通知内容框 Figma 独立复读、重复导出及来源内容框像素 QA PASS；非文字区 24,744 像素中仅四个圆角 56 像素因阴影边缘合成有差异，其他像素完全一致，标题和正文完整。`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-091: Drawer 固定“详情 / 抽屉内容”右侧打开态的官方源码/CSS、真实浏览器 Component IR、320×500 截图和来源锁 PASS；Component IR 契约补列 Drawer 类型。Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-092: Drawer 固定详情面板 Figma Inter 原生主组件/实例、来源颜色变量及阴影、独立读回和重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-093: Drawer 固定详情面板 Figma 独立复读、重复导出及来源面板像素 QA PASS；非文字区域 151,464 像素完全一致，标题和正文完整。`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-094: Upload 固定“上传文件”拖拽空态的官方源码/CSS、真实浏览器 Component IR、320×82 截图和来源锁 PASS；Component IR 契约补列 Upload 类型。Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-095: Upload 固定拖拽空态 Figma Inter 原生主组件/实例、来源颜色变量、虚线边框、独立读回和重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-096: Upload 固定拖拽空态 Figma 独立复读、重复导出及来源像素 QA PASS；非文字区 23,265 像素中仅外边缘 667 像素因虚线栅格化有差异，框内部完全一致，文字完整。`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-097: Cascader 固定“浙江 / 杭州”两级选中闭合态的官方源码/CSS、真实浏览器 Component IR、240×32 截图和来源锁 PASS；Component IR 契约补列 Cascader 类型。Figma 候选与单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-098: Cascader 固定两级地区选中态 Figma Inter 原生主组件/实例、复用已准入 Select 几何与官方箭头、来源颜色变量、独立读回和重复 PNG/SVG 候选审计 PASS；单端 QA 尚未执行，双端正式准入仍 DEFERRED。
- TASK-099: Cascader 固定两级地区选中态 Figma 独立复读、重复导出及来源像素 QA PASS；非文字及箭头区 3,910 像素中仅四角 41 像素抗锯齿有差异，其他像素完全一致，文字与箭头完整。`admissionEligible=false`，双端正式 Fidelity Gate 与 Registry 准入仍 DEFERRED，V0.2 仍 NOT_READY。
- TASK-100: 十八类目标组件的 Figma 证据只读总审计 PASS：7 类固定配置双端正式准入，另 11 类 Figma 单端独立 QA，Figma 侧 18/18 类具备可核验来源/原生证据。`releaseReady=false`；Penpot 暂缓、Adapter 字节锁架构冲突及新独立原型全量 Release Gate 仍未完成。
- TASK-101: Figma 覆盖审计补齐 11 类组件的原生读回、首次/重复 PNG、SVG 逐文件哈希和单端准入边界检查；篡改重复导出被拒绝，定向 3 项测试 PASS，审计仍 `FIGMA_EVIDENCE_COMPLETE`、`releaseReady=false`。
- TASK-102: 用户批准版本化逐端 Adapter 字节锁迁移方案；新 V0.2 任务已实现原始源码字节、两端计划及创建脚本锁，受控导出 Figma 执行脚本并拒绝锁漂移/脚本篡改，旧锁与历史证据保持不变。冻结列表样张在 Figma 新页实际执行，独立读回的 6 个实例/25 个文字节点与计划一致、1920×1080 原生 PNG 重复字节一致，单端样张 QA PASS。正式执行回执持久化、新独立原型及 Penpot 原生线仍待完成，V0.2 仍 NOT_READY。
- TASK-104: 同一字节锁在 Figma 新页完成第二次原生执行，并保存完整回执；49 个 UI-IR 节点映射和执行证据与计划/独立读回一致，6 个实例、25 个文字节点和重复 PNG PASS。机器审计核对回执篡改会 FAIL；Figma 冻结样张的执行回执已持久化，仍不是新独立原型或 V0.2 全量发布。
- TASK-105: Adapter 执行锁修正为逐端失效；Penpot 锁漂移不再误挡 Figma 执行，定向 3 项测试 PASS。新锁绑定的新 Figma 页面 `237:2` 实际执行与完整回执、独立读回、6 个实例/25 个文字节点、重复全尺寸 PNG 机器审计 PASS。TASK-102/104 保留为旧代码字节快照，不原地迁移；V0.2 仍 NOT_READY。
- TASK-106: Adapter 锁漂移改为 `MIGRATION_REQUIRED` 且保留九阶段 Checkpoint 与 `final_ui_ir.json`；定向 3 项测试 PASS。新代码字节锁绑定 Figma 新页 `238:2`，49 项完整执行回执、独立读回、6 个实例/25 个文字节点和重复原生 PNG 审计 PASS；旧锁仅保留为历史快照，V0.2 仍 NOT_READY。
- TASK-107: 新增只读当前就绪审计，重算 18 类 Figma 覆盖与 TASK-106 当前 Figma 字节锁原生回执；18/18 Figma 证据、7 类正式准入、11 类单端 QA、Figma 锁 PASS，Penpot 与独立新原型/全量发布门仍待办。`evidenceValid=true`、`releaseReady=false`，重复 PNG 篡改拒绝测试 PASS；TASK-053 历史快照不变。
- TASK-108: 用户批准另一份用户管理紧凑查询原型；新的源码/语义/人工审核回执、两行查询布局与右对齐按钮、7 项语义和独立 UI-IR 经九阶段 Core PASS。Figma 新页 `240:2` 实际执行、37 项完整回执、5 个真实实例/21 个文字节点、重复原生 PNG 和目视复核 PASS；九阶段断点复用 PASS。Figma 独立原型 E2E 已闭合，Penpot 与全量发布门仍暂缓/未完成。
- TASK-109: 新独立原型的 Figma 单端发布门九项 PASS；21 个原生文字节点的字体与裁剪祖先边界独立读取全部通过，实际视觉复核绑定原生 PNG 哈希，字体/视觉证据篡改测试拒绝。当前就绪汇总仍 `releaseReady=false`，Penpot 原生执行、11 类双端准入及全量 Release Gate 未完成。
- TASK-110: 生产 CLI 新增显式 `v0.2.6` 七组件 Profile，并把已审核紧凑查询原型隔离迁移到新版输入锁；旧输入直接被新版拒绝，原型文字/审核语义不变。九阶段 Core、双端静态预检、新 Adapter 字节锁及 Figma 新页 `243:2` 原生执行 PASS；37 项回执、5 个实例/21 个文字、重复 PNG、独立 QA 与九项 Figma 单端发布门均 PASS。该页面实际使用四类组件，新增三类在 Profile 中可用但未由此页验证。当前就绪仍 `releaseReady=false`。
- TASK-111: `v0.2.6` 七个已准入 Figma 主组件逐页只读原生复读并与生产绑定、固定内容、尺寸、字体及 Fidelity 哈希核对 PASS；Tag、Checkbox、Radio 虽未被 TASK-110 页面使用，其当前 Figma 主组件引用存活。审计拒绝文案或引用篡改；不扩大双端准入或发布结论。
- TASK-112: 将 TASK-111 七组件 Figma 主组件审计纳入当前发布就绪汇总，固定文案漂移将使总证据 `INVALID_EVIDENCE`；新报告 `evidenceValid=true`、`releaseReady=false`。README 和发布就绪说明已更新当前 Figma/Penpot 进度，旧报告不覆盖。
- TASK-113: 新增 `v0.2.6` 生产准入边界审计：7 个正式组件均可解析且与 Registry、admission、双端绑定一致；11 个 Figma 单端候选均返回 `missing_component`，不在生产绑定中。私自加入候选绑定的测试 FAIL，当前就绪汇总加入该门并仍为 `releaseReady=false`。
- TASK-114: V0.2.6 紧凑查询输入迁移改为已有目标先验锁与语义：原目标完全一致即复用、无写入；内容被修改且同步改写清单哈希时仍拒绝覆盖。隔离新建包逐文件与已验收包字节一致，相关回归 7 项 PASS，当前证据仍有效且整体未发布。
- TASK-115: V0.2.6 新输入迁移改为仓库内同级隔离目录生成、自验后移动；结构门失败不留下目标或临时目录，仓库外目标被拒绝。已有目标继续只读复用；相关回归 9 项 PASS，当前发布状态不变。
- Pending scope: [V0.2 Autonomous Development Plan](../docs/DEVELOPMENT_PLAN_V0.2.md)。
- TASK-116: 用户明确将 Penpot 全线搁置。新增 Figma-only 生产入口，当前 V0.2.6 紧凑查询输入九阶段 Core 与 Figma Adapter 预检 PASS，仅产出 Figma 字节锁；无 Penpot 文件参数、预检或活动验收门。新 Figma 锁内的平台源码/计划哈希与 TASK-110 已原生执行且九项单端发布门通过的锁完全一致；TASK-116 自身尚未执行新的原生页面。定向回归 5 项 PASS。详见 [范围决策](TASK-116_FIGMA_SCOPE.md)。
- TASK-117: 11 类剩余 Figma 候选改为一次批量核验，逐类输出来源 Component IR／官方截图／Figma 原生 QA／独立导出哈希链；11/11 PASS、0 问题，7 类固定内容范围需集中补齐。篡改来源身份会阻断整批；定向 5 项测试 PASS。尚未变更正式 Registry 准入；批量迁移的架构冲突与建议见 [TASK-117](TASK-117_FIGMA_BATCH.md)。
- TASK-118: 用户批准版本化 Figma-only 批量准入。新增独立 `0.2.7` Registry：原有 7 类固定配置与新增 11 类官方运行属性／原生可见文字／尺寸快照，共 18 类均可解析且绑定到已核验 Figma 主组件；旧版不变。新独立原型迁移、九阶段 Core、Figma 预检、新字节锁及 Figma 原生页面 `252:1244` 执行 PASS；独立复读 5 个实例、21 个文字，重复原生 PNG 与视觉复核 PASS，10 项单端发布门全 PASS。首轮编码损坏草稿已删除并以无损传输重跑。详见 [TASK-118](TASK-118_FIGMA_BATCH_ADMISSION.md)。
- Next action: 当前定义的 Figma 固定配置范围已通过批量准入与单端发布门。后续扩展不同文字、尺寸或状态须另做来源与保真准入；历史双平台 V0.2 发布目标不作为当前任务队列，也不得把单端结果写成双端发布通过。
- TASK-119: 新增 Figma 组件批次规划入口：逐项区分已准入配置复用、新配置官方采集和既有逻辑 ID 变更迁移；18 个现有固定配置可在一次批次全部复用。Figma-only 发布审计消除重复的 11 类候选重审，仍由 Registry builder 执行完整来源核验并保留 10 项发布门。未新增组件、原生页面或放宽视觉门；详见 [TASK-119](TASK-119_FIGMA_BATCH_WORKFLOW.md)。
- TASK-120: 18 类已准入 Figma 主组件用一次只读原生调用取得 ID／页面／尺寸／文字／字体，批量审计 18/18 PASS，变更文案、引用或尺寸会逐项 FAIL。编译入口从 V0.2.7 Registry 与绑定生成同批脚本；审计工具置于 Adapter 目录外，旧执行锁及 10 项单端发布门仍 PASS。无新变体或页面；详见 [TASK-120](TASK-120_FIGMA_BATCH_NATIVE_READ.md)。
- Background execution: 未配置，不因公开发布或读取计划而启动。
- TASK-121: 用户明确要求把主流程调整为统一内容 Tree、保留彩色组件骨架原生页、另建默认文案组件页、后填原型内容和最终原型逐项校对；架构决策见 [TASK-121](TASK-121_WORKFLOW_DECISION.md)。新增 V0.3 分阶段契约、Figma 骨架／文案填入脚本与独立 QA 门；已用 TASK-118 冻结原型生成新准备产物，Tree/骨架计算完整，原生页面执行与最终校对仍 NOT_RUN，不能宣称新流程已完成原生验收。Penpot 继续搁置，旧任务字节锁不迁移。
- TASK-122: V0.3 content/native stage gates passed on pages 259:2 and 261:2, but this is no longer a compliant deliverable: the subsequently specified iView standard fails on four palette tokens and a synthetic Table header. Historical stage evidence remains; see [TASK-122](TASK-122_WORKFLOW_NATIVE_SMOKE.md). Penpot remains deferred.
- TASK-123: User specified iView/View UI Plus as the design norm. An official-source-bound audit now blocks new native stages when known iView palette or native Table-header rules fail; TASK-122 audit is FAIL. A source-bound Figma headed Table and separate corrected skeleton, default-copy and filled-page candidates exist, but formal Registry, Core and Adapter migration and full stage QA remain open; see [TASK-123](TASK-123_IVIEW_CONFORMANCE_CONFLICT.md).
- TASK-124: 用户要求 skill 本身从原型提取内容后主动按规范补页面布局。已记录[架构冲突与批准方向](TASK-124_LAYOUT_INTENT_ARCHITECTURE_CONFLICT.md)，新增 V0.3.2 列表页项目布局规则、模型布局意图契约及独立质量门。TASK-122 冻结布局因页头／列表零内边距和 1392 px Table 无法填满内容区而 FAIL；合规计算样本 PASS；新原生骨架缺该门 PASS 时阻断。未修改 Figma 页面或旧锁，正式 1840 px Table 组件准入与新页面运行仍待后续任务。
- TASK-125: 仅取 TASK-122 原型原文，在全新 `artifacts/task-125` 独立重建语义观察、Tree、布局意图与试算；语义和 Core 几何试算 PASS，V0.3.2 规范化布局门因正式 Table 1392 px 与所需 1840 px 不符而 FAIL，iView 资源预检另发现四项色彩 Token 与原生表头能力缺口；原生入口按门阻断，未创建新 Figma 页面。试算使用显式 test-fixture，非生产测量；详见 [TASK-125](TASK-125_INDEPENDENT_SKILL_TRIAL.md)。
- TASK-125 恢复验收：按用户要求追查 FAIL 并继续，新版 1840 px 原生表头 Table、0.2.8 组件库、0.2.3 Token 和 Figma-only 绑定已完成；新任务原生测量替代试算尺寸，Core、Figma Adapter、iView 有界规则及 V0.3 全阶段 QA PASS。保留骨架页 `288:2`，最终页 `289:2`；乱码骨架候选已排除。详情见 [TASK-125 恢复验收](TASK-125_RECOVERY_ACCEPTANCE.md)。Penpot 仍搁置，旧版任务锁不迁移。
- TASK-126: 新 Figma-only 路径在完整 Core 前检查已知组件和来源能力，骨架脚本前预编译默认组件页，生成脚本使用 ASCII/Unicode 转义；目标是把 TASK-125 中的可预见 FAIL 前移为资源/输入诊断，避免原生写入后返工。针对性 13 项测试与 Skill 格式校验 PASS；全仓旧证据依赖未齐，结果和边界见 [TASK-126](TASK-126_FAILURE_PREVENTION.md)。Penpot 与历史锁未迁移。
- TASK-127: 用户要求移除所有固定尺寸准入条件。新增独立 Figma-only V0.2.9 内容/尺寸分离版本、可自适应原生 Table 主组件与 1660 px 实例；所有 19 个内容范围不再以样本宽高或列像素宽度准入。1740 画布/1660 Table 的预检、九阶段 Core、Adapter 和规范布局门 PASS；原生组件截图及读回已保存，未宣称整页原生 QA 完成。详见 [架构决策](TASK-127_DIMENSION_POLICY_DECISION.md)和[验收记录](TASK-127_ADAPTIVE_SIZE_ACCEPTANCE.md)。旧版本与 Penpot 不迁移。
- Historical validation: 本目录相应验收记录；公开快照检查见 `docs/PUBLICATION_VALIDATION.md`。

保留V0.1来源和版本锁。V0.2使用新版本与新验收目录，不覆盖历史批准和失败。
