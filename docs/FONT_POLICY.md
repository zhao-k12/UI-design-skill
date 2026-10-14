# 新设计字体政策

用户于 2026-10-12 明确选择：设计字体使用 Figma 和 Penpot 各自的默认字体。

新 V0.2 任务采用 `policies/font-selection-0.2.0.json`。目标文件中的实际默认字体已在 TASK-024 验证：Figma 为 Inter，Penpot 原生 family/id 为 sourcesanspro；两个平台的 400/600 样张通过视觉复核。更换目标文件时仍须重新观测默认字体，不从当前目标推断其他文件。

实际生成前，从目标平台读取原生 Text 的默认字体及可用样式，检查所需文字与字重，保存解析后的字体、平台引用和观察证据。完成测量后再布局；同一语义角色可在两个平台解析为各自的默认字体。字体与节点引用只留在 Adapter Metadata，不写入平台无关 Core。

新设计不依赖本机安装或上传苹方，不自行上传字体。默认字体或所需字重/字形不可用时记录 Missing/Unsupported，不静默替代或捏造 PASS。

历史 V0.1、组件库 0.2.1/0.3.0 和字体保真证据保持原有版本锁。已准入组件不能直接更换字体继续沿用旧保真 PASS；需要在新版本重新测量、实际生成与验收。历史字体探针的同字节文件路径迁移仅用于复验旧记录，不是新设计的字体选择流程。

TASK-024 的临时字体探针已清理。Button、Input、Select、Table 的固定配置已依次通过双平台新保真门，进入独立 V0.2.3 Registry；其他配置仍须逐项测量与验收。TASK-042 新增平台无关的 `platform-default` 页面文字 Token，Adapter 根据各自目标文件观测元数据解析为 Inter Regular 400 或 `sourcesanspro` regular 400；TASK-052 已以冻结列表页完成双平台原生整页验收。具体中文回退字体身份未核实，不以原生字体家族名推断。详见 [默认字体预检](DEFAULT_FONT_PREFLIGHT.md)、[TASK-041 验收](../.dev/TASK-041_ACCEPTANCE.md)、[TASK-042 验收](../.dev/TASK-042_ACCEPTANCE.md) 和 [TASK-052 验收](../.dev/TASK-052_ACCEPTANCE.md)。
