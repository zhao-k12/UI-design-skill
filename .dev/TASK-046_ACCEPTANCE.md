# TASK-046 — V0.2.2 静态画布最小高度

日期：2026-10-14。状态：PASS（Core 布局与双端 Adapter 预检）；完整原型到原生页面流水线仍 BLOCKED。架构决策见 [TASK-046_ARCHITECTURE_CONFLICT.md](TASK-046_ARCHITECTURE_CONFLICT.md)。

新增独立 Token 快照 `registries/tokens/v0.2.2/default.json` 和 Schema。相对 V0.2.1，Token 映射仅增加 `size.page-min-height=1080`；页面宽度仍为 1920，字体仍为平台默认字体。布局生成器按 Token 版本显式选择静态增高策略，Page 高度为 `max(1080, contentHeight)`。短内容获得 1920×1080，长内容自然增高，未引入滚动、固定栏或交互状态。旧版本快照和默认 Pattern 路径不变。

验证：75 项相关单元及 Adapter 测试通过；`git diff --check` 通过。短页、长页、旧版本隔离、Builder 路由均有回归测试。同一 TASK-043 UI-IR 使用 V0.2.2 Token 的 Figma/Penpot Adapter 预检均 `PASS`、0 issues，`nativeExecution=NOT_RUN`；报告位于 `artifacts/task-046/{figma,penpot}`。迁移审计在 `artifacts/task-046/readiness_report.json`，最小高度阻塞已解除，仍有 5 项：旧输入版本锁、来源几何、Penpot 新文件图标绑定、CLI V0.1 固定路由、文字测量重绑定。

本任务没有创建新的原生页面。完整流水线及最终页面验收须待上述阻塞解除后进行；TASK-043 的双端原生样张验收仍仅覆盖 Adapter 契约范围。
