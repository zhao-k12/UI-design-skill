# V0.2 发布就绪状态

截至 2026-10-14：**NOT_READY**。只读 [机器审计](../artifacts/task-053/release-readiness.json) 验证当前证据字节与范围；`evidenceValid=true` 表示现有证据一致，不表示已通过全量发布门。重新运行：

2026-10-15 增量：Tag、Checkbox、Radio 各一个固定配置已陆续准入独立 V0.2.4、V0.2.5、V0.2.6 Registry，当前为 18 类目标中的 7 类，仍有 11 类未准入。下表保留 TASK-053 在 2026-10-14 的只读审计快照，不代表今日覆盖数；V0.2 整体仍 **NOT_READY**。

2026-10-20 Figma 线增量：18 类目标现均具备来源和 Figma 原生证据；其中 7 类已有双平台正式固定配置准入，另 11 类完成 Figma 独立单端 QA，未进入正式 Registry。新的 [覆盖审计](../artifacts/task-100/coverage-audit.json)核对 18/18 类的证据哈希及准入边界，结果 `FIGMA_EVIDENCE_COMPLETE`、`releaseReady=false`。用户已决定暂缓不稳定的 Penpot 连接，双端保真与全量发布门保持待办。

TASK-101 进一步核对 11 类组件的原生读回、首次/重复 PNG 与 SVG 字节，并在重复导出被篡改时拒绝证据；这是 Figma 单端证据完整性检查，不改变正式准入数。

Adapter 字节锁 [版本化迁移方案](../.dev/TASK-102_ADAPTER_BYTE_LOCK_PROPOSAL.md)已获批准，新 V0.2 任务的预检锁与执行脚本受控导出已实现；冻结列表样张的 [Figma 原生读回审计](../artifacts/task-102/figma-native-qa.json) PASS。正式执行回执持久化、新独立原型与 Penpot 原生发布锁仍未完成，不据此改变 `NOT_READY` 结论。

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

下一步继续把 Adapter 字节锁的真实执行回执持久化，并准备独立新原型；Penpot 原生线在用户决定恢复前保持暂缓。V0.2 全量发布前，11 类 Figma 单端组件仍须双平台正式准入，且需以独立新原型执行 A–H 阶段和全部 Release Gate；不能从 TASK-052 或 TASK-102 冻结列表样张的 PASS 外推。
