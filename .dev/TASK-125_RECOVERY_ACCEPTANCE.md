# TASK-125 独立试跑：FAIL 恢复与最终验收

- 范围：仅复用 `examples/workflow-v03-smoke-figma/prototype.txt` 的原型原文；语义、布局、测量、组件资源和原生页面均为 TASK-125 新修订。Penpot 按用户要求搁置。
- 原型 SHA-256：`a112c269ea5fe956007818e52456fb86bb5ce07da14c9e11bed33d922c17b954`。
- 第一次布局 FAIL：正式旧 Table 只有 1392 px，列表内容区要求 1840 px；旧组件没有原生表头，旧 Token 也有四项 iView 色彩不符。未把 FAIL 当作任务完成。
- 修复：从锁定的 View UI Plus 1.3.24 源码重新提取 1840×182.875、原生表头、三列三行 Table；Figma 原生主组件 `280:3`、实例 `280:36`，独立读回和重复 PNG／SVG 证据通过。迁移到独立组件 Registry 0.2.8、Token 0.2.3 与 Figma 绑定；旧组件与旧版本保留。
- 第二次 Core FAIL：旧装配逻辑给已有原生表头的 Table 又叠加合成表头。已改为核对表头来源文案后直接使用关联实例；旧无 scope 测试路径兼容。最终 Core 与 Figma Adapter 预检 PASS，执行锁 `24e0fff4731b1e67de385995a311e5751516a2189c04e7461e339072cf02d8e8`。
- 第三次骨架 QA FAIL：Windows 脚本输出把中文传成乱码。改用 UTF-8 新 revision 重建；错误候选仅保留诊断，未进入默认组件页。
- 最终来源测量来自本次 Figma 独立读回，不使用试算的 test-fixture。Tree、规范布局、iView 已覆盖阻断规则、彩色骨架原生读回、默认文案组件页原生读回、原型文案填入读回、最终 PNG 原型逐项校对全部 PASS；见 `artifacts/task-125/r4/staged/workflow_qa.json`。iView 门只涵盖源码锁、页面配色和原生表头，并非全部官方规范。
- 保留彩色骨架页：`288:2`；最终组件页：`289:2`；目标 Figma 文件：`0vGWSRoLxBiVPXiZ8xJAX9`。最终 PNG：`artifacts/task-125/r4/staged/final-page.png`，SHA-256 `01765dafd308ef8e75b4dd2c5d55b1250c8c5cc7dc4301822c1d8bf0aeff7b30`。
- 最终代码重跑的 Core 与 Figma 预检 PASS，UI-IR SHA-256 `1db08e10cfdc722b278e496ceb2baaa71742b27007a31d0fa03c762cbc593b8a` 与先前原生页面计划一致。回归：核心组 193 tests PASS；相关旧组件／流水线 45 tests、5 subtests PASS；新增 0.2.8 资源测试 PASS。
- 本次修复只扩展固定配置准入与带表头 Table 的窄路径，不改变 Core 的平台隔离、UI-IR 或旧版结果。此前 TASK-125 FAIL 报告保留为历史试算记录，不能作为最终结论。
