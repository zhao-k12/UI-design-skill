# TASK-102 — Adapter 字节锁预检与执行脚本导出

日期：2026-10-20。状态：**FIGMA_SAMPLE_NATIVE_PASS / RELEASE_NOT_READY**。用户批准 [版本化迁移方案](TASK-102_ADAPTER_BYTE_LOCK_PROPOSAL.md)。新任务的 `adapter-execution-lock.json` 记录 `0.2.0` 契约、两端预检计划 SHA-256、目标文件/UI-IR、逐文件原始字节哈希及每页创建脚本哈希。共享 Adapter 源、两端 Adapter Python/JS、生产入口和复验入口进入锁范围；metadata 与历史证据不纳入可执行代码集合。

V0.2 生产预检仅在两端计划 PASS 后写入锁；同一任务目录同字节恢复允许复用，锁变化即拒绝并要求新任务目录。独立导出入口 `scripts/prepare_adapter_execution.py` 从已锁计划生成精确原生脚本与 `execution-intent.json`，重复导出保持字节一致，已存在文件若被改动则拒绝。此回执只说明 **READY_TO_EXECUTE**，保留 `nativeExecution=NOT_RUN`、`releaseReady=false`，不冒充平台执行证明。

验证：相关 Core、Figma/Penpot Adapter、Figma 覆盖审计共 34 项 PASS。新增断言覆盖同字节恢复、锁中源码哈希变化、脚本字节篡改、已导出脚本篡改和锁变化后的 CLI 拒绝。V0.1 路线未增加此新锁。

Figma 样张：以现有冻结列表输入运行 [新锁](../artifacts/task-102/run/adapter-execution-lock.json)，导出 [执行意图](../artifacts/task-102/figma-execution-page/execution-intent.json)，在用户指定 Figma 文件的新页 `233:811` 实际执行；返回 `PASS`，根节点 `234:2`。独立 [原生读回](../artifacts/task-102/figma/native-read.json)和 [全尺寸 PNG](../artifacts/task-102/figma/native.png)核对 1920×1080、6 个真实实例、25 个文字节点，重复 PNG SHA-256 均为 `d8319e83cacb017a154dcb49138aa324639b31115a368fe645b3e59347b6b3cd`。 [机器审计](../artifacts/task-102/figma-native-qa.json) PASS；篡改重复 PNG 时 FAIL。已目视检查无裁切或重叠。这仅验证冻结样张的 Figma 端，执行工具完整回执未另存为独立文件。

本轮补装 Brotli 后，全量基线 `unittest discover -s tests -v` 运行 646 项，结果 30 ERROR、1 FAIL。已独立确认部分历史测试依赖仓库缺失的 `.dev/TASK-019_ARIAL_ENCODING_DECISION.md`、旧机器 `F:\\zo2026\\...` 与专有字体路径；这些证据不能伪造或改写旧锁，故全量回归不记为 PASS。TASK-102 新实现的定向结果以实际测试输出为准。

后续仍须将 Figma 真实执行回执持久化并与脚本哈希严格绑定，再用独立新原型验收。Penpot 原生执行按用户决定暂缓；V0.2 全量 Release Gate 尚未完成。
