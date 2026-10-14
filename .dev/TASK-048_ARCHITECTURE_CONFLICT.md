# TASK-048 — ARCHITECTURE_CONFLICT: 生产 CLI 固定 V0.1 资源路径

日期：2026-10-14。状态：以显式版本路由解决 CLI 资源选择。

## 当前设计

`scripts/run_pipeline.py` 无条件读取 V0.1 组件、Token 和双端绑定。Adapter 独立 CLI 已支持 V0.2.3 组件和 V0.2.2 Token，但完整流水线无法选择它们。

## 原因与影响

若直接替换默认路径，旧验收输入会隐式迁移，破坏 V0.1；若只在末端 Adapter 切换，Core 与原生绑定会使用不同 Registry。V0.2 新输入包尚缺默认字体测量和当前 Penpot 图标证据，也不能因新增路由而跳过质量门。

## 决策与实施边界

CLI 增加显式 `--profile v0.2`，默认 `v0.1`。同一 profile 决定 Core Registry、Token、双端组件绑定和字体绑定；输入 `versions.json` 必须与所选资源一致，且锁不匹配时在运行前失败。保留 Runner 的 manifest/checkpoint 机制，不重构 Core 主链；不创建 V0.2 输入包，不把路由就绪解释为流水线验收通过。
