# TASK-042 — V0.2 页面自由文本的双平台默认字体预检

日期：2026-10-13。状态：PASS（Adapter 预检）；原生页面执行未运行。架构冲突与版本边界见 [TASK-042_ARCHITECTURE_CONFLICT.md](TASK-042_ARCHITECTURE_CONFLICT.md)。

新 `registries/tokens/v0.2.0/default.json` 将页面标题和正文的字体族记为平台无关的 `platform-default`。当前两种角色只使用已在替代 Penpot 文件中观测的 Regular 400；字号、行高沿用本项目已有角色尺寸。Adapter 的新字体绑定记录锁定目标文件 ID 和默认字体观测元数据 SHA：Figma 解析为 Inter Regular，Penpot 解析为 `sourcesanspro` regular。错误文件、错误原生 family 和未观测的 600 字重均被拒绝。V0.1 Token、显式字体绑定和默认 CLI 版本保持原样。

共享契约输入为 `examples/v02-default-font-adapter-contract.ui-ir.json`（SHA-256 `cf0245cfa014c0c9457a4e5f908ea542d7d59768785536f8dd7704b0484f7717`），包含 1920×1080 Page、一处自由标题 Text 和 V0.2.3 已准入的 Button、Input、Select、Table。它是 Adapter 契约样张，不代表原型理解到页面生成的完整链路或最终页面设计。Token 快照 SHA-256 为 `13c78686e58a8b8b5ac08cb409bc20dfd673f0ae15a4eac9f7cebbe117341a8e`；两端字体绑定 SHA-256 分别为 `0b7cfe68422fd703f5cee1d088ff2da8b4341edb577ebb7faabed7cd89cfdf02`、`74fe0f1f60cf2f116c6cafe1d3c72290bdc5c2785052df4eeb605c9db979e0df`。

实际运行两端 CLI，均以 `--component-library-version 0.2.3 --token-library-version 0.2.0 --font-bindings <平台绑定>` 预检，输出 `status=PASS`、0 issues、`nativeExecution=NOT_RUN`；报告和宿主脚本在 `artifacts/task-042/{figma,penpot}`。30 项新旧 Adapter、字体及架构测试通过。页面原生创建、独立读取、截图与视觉验收留待后续任务，不能从本次预检推断完成。
