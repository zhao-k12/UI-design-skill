# TASK-048 — 生产 CLI 显式 V0.2 Profile

日期：2026-10-14。状态：PASS（资源路由与旧版回归）；完整 V0.2 流水线仍 BLOCKED。架构决策见 [TASK-048_ARCHITECTURE_CONFLICT.md](TASK-048_ARCHITECTURE_CONFLICT.md)。

`scripts/run_pipeline.py` 增加 `--profile v0.2`。选中后，Core 使用 V0.2.3 组件 Registry 与 V0.2.2 Token，双端 Adapter 使用同版组件绑定和经观测的平台默认字体绑定。默认 `v0.1` 路径保持原样。CLI 在运行阶段前核对输入 `versions.json` 与所选 Registry/Token，不允许冻结 V0.1 输入隐式迁移；现有 Runner 的 manifest/checkpoint 锁继续生效。此任务没有创建完整 V0.2 输入包。

13 项相关测试通过，覆盖两个 Profile 的资源存在性、相互隔离、错误输入在输出创建前拒绝及原流水线回归。旧验收原型经默认生产 CLI 再运行，Core 与双端 Adapter 预检均 `PASS`，结果位于 `artifacts/task-048/v01-regression`，原生执行和最终视觉 QA 均 `NOT_RUN`。结合 TASK-047 几何包重新审计，报告位于 `artifacts/task-048/readiness_report.json`；CLI 固定路由阻塞解除，剩余三项为旧输入版本锁、Penpot 新文件图标和文字测量重绑定。`git diff --check` 通过。

当前未运行 V0.2 完整原型到页面链路，也未创建新的原生页面。后续须备齐新输入证据及图标绑定，再用该 Profile 运行完整质量门。
