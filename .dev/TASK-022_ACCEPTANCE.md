# TASK-022 — 可移植证据包契约与完整性工具

日期：2026-10-12。授权：用户在 TASK-021 完成及可移植证据包下一步建议后要求“继续”。

## 范围

新增自包含证据包契约、打包工具、只读完整性校验和开发日志包验证。复用已锁定 jsonschema 4.26.0 与 Python 标准库。契约位于 scripts/evidence-package.schema.json，不新增 Core/Schema/Validator 文件，因此不改变 V0.1 程序指纹范围。历史 manifest、正式 Registry、平台执行器、来源锁、package.json 和 lockfile 均未修改。

## 交付

- 契约 0.1.0：artifact 身份、原始哈希与大小、分发声明、版本锁、配置覆盖及平台证据角色引用。
- scripts/evidence_package.py：先聚合缺项与非法路径；新临时目录写入、完整复验后重命名；拒绝覆盖已有包。verify 不依赖原来源目录。
- tests/test_evidence_package.py：15 项测试，覆盖移除来源并复制包、文件缺失/变化聚合、未列出 payload、跨平台路径、ID/路径/文件目录冲突、禁止覆盖、分发声明、原生角色/版本/平台缺项、引用匹配、重复 JSON、额外字段和完整性成功不等于原生验收。
- core 测试组纳入新测试；文档见 docs/PORTABLE_EVIDENCE.md。

## 实际验证

环境：Windows、Python 3.11.9、Node 24.15.0；全部命令通过 rtk 前缀。

| 检查 | 结果 |
|---|---|
| Draft202012Validator.check_schema | PASS |
| 新证据包测试 | 15 项 PASS；路径保护细化后再次通过 |
| scripts/run_checks.py --group core | 129 项 PASS，42.288 秒 |
| 实际开发日志打包 | PASS；artifact 是本次 core/tests.log，保持原始字节 |
| 复制到新目录后 verify | PASS |
| 修改独立副本的日志后 verify | 按预期 FAIL，code artifact_changed，退出 1 |
| 官方完整来源锁 | PASS |
| git diff --check | PASS |

产物：artifacts/task-022/core/{environment.json,checks.json,tests.log}，plan.json，development-bundle/manifest.json，build-report.json，relocated-report.json 和 tampered-report.json。实际完整性报告均固定 nativeExecution NOT_RUN、nativeAcceptance NOT_RUN、releaseReady false。负向实验仅修改新建 tampered-bundle，不修改来源或完整副本。

打包计划与本次生成的测试日志留在被忽略的 artifacts 中；没有对外发布。这里交付的是开发证据包，没有新原生组件准入，也没有恢复旧版缺失的账号截图或决定。

## 限制与下一步

完整性工具检查文件字节和引用关系，不验证证据内容的原生语义或分发声明的法律真实性，不将十四类角色齐全认作保真 PASS。新正式组件库仍需真实官方提取、合法字体证据、实际目标执行、独立读取/PNG、视觉检查和对应的语义验收器。

下一增量先准备可重放的官方 runtime 环境与来源证据，再为最小组件配置建立新版本真实证据。组件覆盖、Canvas 和假设政策仍按 V0.2 计划限定范围，不因本任务自动批准。
