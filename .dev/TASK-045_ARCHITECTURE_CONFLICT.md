# TASK-045 — ARCHITECTURE_CONFLICT: V0.2 画布宽度与 Token 冻结

日期：2026-10-14。状态：限定新版本快照的解决方案。

## 当前设计

V0.2.0 Token 沿用旧 `size.page=1440`，而 Layout Pattern 的 Page 固定引用 `size.page`。V0.2 计划、用户指定目标以及 TASK-043 双平台原生样张均采用 1920×1080。若直接以 V0.2.0 Token 运行完整流水线，Page 仍为 1440，与目标不符。

## 原因与影响

修改 V0.2.0 原文件会改变 TASK-042/043 已锁定的 Token SHA 和宿主脚本来源；修改 V0.1 基线会破坏历史验收。为弥补宽度而在 Adapter 中拉伸 Page 则违反布局由 Core 确定的边界。长内容高度策略尚未决定，本次不从宽度规则推断滚动或增高政策。

## 决策与实施边界

新增 V0.2.1 Token 快照，仅将 `size.page` 改为 1920，保留所有默认字体和其他 Token 值。版本化 Schema 与两个 Adapter CLI 显式接受该版本；旧快照和默认选项保持原样。通过 Layout Pattern 及双端 Adapter 预检验证新版本。后续完整流水线必须使用新输入/Manifest 锁，不把 TASK-043 原生页面冒充 V0.2.1 产物。
