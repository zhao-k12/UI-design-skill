# V0.2 发布就绪状态

截至 2026-10-14：**NOT_READY**。只读 [机器审计](../artifacts/task-053/release-readiness.json) 验证当前证据字节与范围；`evidenceValid=true` 表示现有证据一致，不表示已通过全量发布门。重新运行：

2026-10-15 增量：Tag 和 Checkbox 各一个固定配置已陆续准入独立 V0.2.4、V0.2.5 Registry，当前为 18 类目标中的 6 类，仍有 12 类未准入。下表保留 TASK-053 在 2026-10-14 的只读审计快照，不代表今日覆盖数；V0.2 整体仍 **NOT_READY**。

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

下一步先为 Adapter 字节锁制定版本化迁移决策，再选择一个有官方来源与双平台保真可验收的有限组件覆盖增量。V0.2 全量发布前，还需以独立新原型执行 A–H 阶段和全部 Release Gate；不能从 TASK-052 的单页 PASS 外推。
