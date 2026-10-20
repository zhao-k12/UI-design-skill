# V0.2 发布就绪状态

当前状态见 [TASK-114 实时重算审计](../artifacts/task-114/current-release-readiness.json)：**NOT_READY**，现有证据有效。18 类目标在 Figma 侧都有证据，7 类固定配置正式双端准入、11 类仅完成 Figma QA。生产 CLI 已提供独立的 `v0.2.6` 七组件 Profile；经用户审核的[紧凑查询原型](../examples/user-management-compact-search-v026/prototype.txt)已迁移并在新锁下通过 Figma 原生端到端与[九项单端发布门](../artifacts/task-110/figma-release-gates.json)。该页面实际使用 Button、Input、Select、Table 四类；Tag、Checkbox、Radio 虽在 Profile 中可用，未在该页面内行使。Penpot 线暂缓，双端及全量 Release Gate 未完成。下方 TASK-053 表格是 2026-10-14 历史快照。

TASK-111 对七个已准入 Figma 主组件做[当前原生引用审计](../artifacts/task-111/figma-master-liveness.json)，核对真实主组件 ID、尺寸、固定文案、默认字体与登记哈希，全部 PASS。Tag、Checkbox、Radio 的主组件引用有效，但 TASK-110 页面仍未使用它们；此项不改变 Penpot 和全量发布状态。

TASK-112 将七组件主组件审计纳入当前就绪汇总，文案漂移会使总证据变为 `INVALID_EVIDENCE`；历史 TASK-110 报告保持原样。README 的现状描述同步更新，明确 Figma 已通过的范围和 Penpot 暂缓项。

TASK-113 增加[生产准入边界审计](../artifacts/task-113/admission-boundary.json)：七个正式组件可解析，11 个 Figma 单端候选均被拒绝且未进入双端生产绑定。该边界现是当前就绪汇总的独立检查项。

TASK-114 加固 V0.2.6 输入迁移：已存在的目标包须通过字节锁和语义复核才可复用，修改后不得被脚本静默覆盖；重新生成的隔离包与已验收输入逐文件一致。该修正不改变当前原生验收结论。

截至 2026-10-14：**NOT_READY**。只读 [机器审计](../artifacts/task-053/release-readiness.json) 验证当前证据字节与范围；`evidenceValid=true` 表示现有证据一致，不表示已通过全量发布门。重新运行：

2026-10-15 增量：Tag、Checkbox、Radio 各一个固定配置已陆续准入独立 V0.2.4、V0.2.5、V0.2.6 Registry，当前为 18 类目标中的 7 类，仍有 11 类未准入。下表保留 TASK-053 在 2026-10-14 的只读审计快照，不代表今日覆盖数；V0.2 整体仍 **NOT_READY**。

2026-10-20 Figma 线增量：18 类目标现均具备来源和 Figma 原生证据；其中 7 类已有双平台正式固定配置准入，另 11 类完成 Figma 独立单端 QA，未进入正式 Registry。新的 [覆盖审计](../artifacts/task-100/coverage-audit.json)核对 18/18 类的证据哈希及准入边界，结果 `FIGMA_EVIDENCE_COMPLETE`、`releaseReady=false`。用户已决定暂缓不稳定的 Penpot 连接，双端保真与全量发布门保持待办。

TASK-101 进一步核对 11 类组件的原生读回、首次/重复 PNG 与 SVG 字节，并在重复导出被篡改时拒绝证据；这是 Figma 单端证据完整性检查，不改变正式准入数。

Adapter 字节锁 [版本化迁移方案](../.dev/TASK-102_ADAPTER_BYTE_LOCK_PROPOSAL.md)已获批准，新 V0.2 任务的预检锁与执行脚本受控导出已实现；冻结列表样张的 [Figma 原生读回审计](../artifacts/task-102/figma-native-qa.json) PASS。该阶段尚未保存完整执行回执，后续 TASK-104 已补齐；新独立原型与 Penpot 原生发布锁仍未完成。

TASK-104 已在新的 Figma 验证页 [保存完整执行回执](../artifacts/task-104/figma-execution/execution-result.json)并通过 [回执/原生读回审计](../artifacts/task-104/figma-native-qa.json)。这使冻结列表样张的 Figma 单端执行证据闭环；独立新原型、11 类组件双端准入和 Penpot 发布锁仍未完成。

TASK-105 将执行校验改为真正逐端失效，并在新的 Figma 页以 [当前字节锁](../artifacts/task-105/run/adapter-execution-lock.json)重新执行冻结样张；[完整回执与原生审计](../artifacts/task-105/figma-native-qa.json) PASS。TASK-102/104 的锁和证据保持其旧代码字节快照，不迁移复用。Figma 当前锁仅在这一限定样张通过。

TASK-106 修复锁漂移时错误清空 Core 成果的问题：现在明确标记迁移需求并保留九阶段 Checkpoint 和最终 UI-IR。审计还核对原生执行回执的三项资源哈希。变更后的 [当前字节锁](../artifacts/task-106/run/adapter-execution-lock.json)在新 Figma 页完成真实执行，[完整回执和独立原生审计](../artifacts/task-106/figma-native-qa.json) PASS；此前锁是各自代码版本的历史快照。全量结论仍为 **NOT_READY**。

```powershell
.\.venv\Scripts\python.exe scripts/audit_v02_release_readiness.py --output artifacts/task-053/release-readiness.json
```

| 发布条件 | 当前证据 | 状态 |
| --- | --- | --- |
| 默认字体与限定组件 | Figma Inter、Penpot Source Sans Pro；V0.2.3 四种固定内容配置通过保真并登记 | 限定范围 PASS |
| 18 类目标组件覆盖 | Button、Input、Select、Table 共 4 类；其余 14 类尚未准入 | PARTIAL |
| 列表页 Core 流水线 | TASK-051 新输入锁，9 个语义项、4 个组件、2 个图标，双端预检 PASS | 限定范围 PASS |
| 双端原生输出 | TASK-052 同一 UI-IR 的 1920×1080 可编辑页面、独立读回、原生 PNG、人工视觉复核 | 限定范围 PASS |
| Adapter 执行代码锁 | Manifest 锁 Adapter 版本号，但未锁编译器、运行器及执行脚本字节；见 [TASK-053 冲突](../.dev/TASK-053_ARCHITECTURE_CONFLICT.md) | NOT_IMPLEMENTED |
| 新独立原型与更广页面模式 | 当前验收基于冻结列表语义；图片理解、其他页面／Section／表格模式及可变内容未完成全链路原生验收 | NOT_RUN／PARTIAL |
| V0.2 全量 Release Gate | 覆盖矩阵范围、版本迁移、恢复和新原型验收仍未闭合 | NOT_RUN |

当前 `policies/component-coverage-0.2.0.json` 是早期计划快照，不能将其中的 `NOT_RUN` 理解为 V0.2.3 四个固定配置尚未准入，也不能原地改写它来扩展准入。实际准入以 `registries/components/v0.2.3/admission.json` 和对应两端绑定为准。除这四项固定配置以外的文本、尺寸、状态和 Props 仍按 Missing/Unsupported 处理。

独立新原型现已在 Figma 单端通过；Penpot 原生线在用户决定恢复前保持暂缓。V0.2 全量发布前，11 类 Figma 单端组件仍须双平台正式准入，且需完成新原型的 Penpot 端到端验收和全部 Release Gate；不能从单端 PASS 外推双端发布。
