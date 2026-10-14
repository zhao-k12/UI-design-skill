# TASK-047 — V0.2 准入来源几何快照

日期：2026-10-14。状态：PASS（来源几何重建与离线审计）；完整流水线仍 BLOCKED。架构决策见 [TASK-047_ARCHITECTURE_CONFLICT.md](TASK-047_ARCHITECTURE_CONFLICT.md)。

新增 `examples/acceptance-prototype-v02/source-geometry.json` 和 `source-geometry-lock.json`。生成脚本从 TASK-023 锁定的官方运行 Component IR 中取已准入的 Button、Input、Select，从冻结原型中取仍匹配准入哈希的 Table；四项逐一与 V0.2.3 Registry 的 Component IR SHA-256 比对，再由 `SourceGeometry` 验证。快照只处理几何，不代表完整 V0.2 输入包已经就绪。旧 `examples/acceptance-prototype` 未改动。

审计脚本增加显式 `--geometry` 参数；默认仍检查旧包。选择新快照的报告保存于 `artifacts/task-047/readiness_report.json`，`source_geometry_mismatch` 已解除，剩余四项为旧输入版本锁、Penpot 新文件图标、CLI V0.1 固定路由和文字测量重绑定。24 项相关测试通过，覆盖准入哈希、篡改拒绝、审计阻塞变化与旧版行为。生成器重复运行所得内存产物与保存快照完全一致；`git diff --check` 通过。

新快照尚未执行双端原生页面生成。下一步须完成其余输入证据和版本迁移，方可启动完整流水线。
