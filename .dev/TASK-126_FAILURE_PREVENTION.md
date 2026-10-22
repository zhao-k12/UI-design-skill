# TASK-126 — Figma 生成前失败预防

范围：仅更新新任务的 Figma-only `v0.2.8-figma` 生成路径和 V0.3 分阶段脚本；Penpot 与历史任务锁不迁移。

TASK-125 的可避免返工包括旧 Table 宽度和表头能力不足、来源配置与固定内容范围不一致、组件页直到骨架原生写入后才编译，以及 Windows 终端传递时中文标签损坏。现在完整 Core 前先生成 `readiness_preflight.json`，检查官方来源锁、iView Token、结构/布局可计算性、映射/文件绑定与 Table 的原生能力。结果为 `READY` 才继续；资源缺口返回 `NEEDS_RESOURCE`，输入缺口返回 `REVISE_INPUT`，原生动作尚未执行。准备骨架脚本时预编译默认组件页；编译失败时不产生骨架脚本。新生成的骨架、组件和填文案脚本均使用 ASCII/Unicode 转义，防止跨终端损坏中文。

验证：新增 8 项预检与脚本测试 PASS；相邻布局/资源测试合计 13 项 PASS；TASK-125 独立输入在新 profile 下 `READY`、完整 Core 与 Adapter 预检 PASS，UI-IR 指纹未变。错误 Figma 文件的端到端输入返回 `NEEDS_RESOURCE` 和四条绑定诊断，`nativeExecution=NOT_RUN`。Skill 格式校验 PASS。

全仓测试为 682 PASS、28 FAIL、4 ERROR。失败集中于旧任务未随当前工作区提供的 `.dev/TASK-019_ARIAL_ENCODING_DECISION.md`、`artifacts/task-009` 等历史原生证据与本机 FreeType DLL；新增测试无失败。未伪造历史证据或放宽旧门。此预检针对当前已知静态 Table 缺口，不能保证未来组件和 Figma 服务永不出错；后续质量门仍必须执行。
