# TASK-023 — 官方 runtime 环境与复验

日期：2026-10-12。准备范围来自用户继续开发要求；后续字体选择按用户新指示转为平台默认字体。

## 结果

- 锁定 Playwright 1.63.0、Chromium 153.0.8010.12 / revision 1243 和 headless shell 1243 已安装。
- 标准下载器出现 ECONNRESET。使用 Chrome for Testing 官方 Google bucket 地址下载同版本 win64 ZIP，校验官方响应的长度/MD5并记录 SHA256，安装后标准 `npx playwright install chromium` 实际通过。
- 新 scripts/runtime_replay.mjs 两次真实官方默认 Button/Input/Select 提取通过；7 个文件逐字节一致，实际 browserVersion 与 Playwright metadata 一致。
- 首次完整 Node 测试为 114 PASS / 1 FAIL，原因是历史字体路径不在本机。本机已有文件 SHA256 与历史要求完全相同；生成独立同字节路径迁移记录，不修改原身份文件或字体字节。
- 使用显式迁移记录再次运行完整 runtime 组：115 项 PASS，0 skipped，30.017 秒。字体探针继续验证实际截图、几何恢复和文件哈希。
- core 最终组：137 项 PASS；报告与日志在 artifacts/task-023/core-final。
- 历史正式 Registry、源码锁、package.json、lockfile、Core/Schema/Validator 和旧验收记录未修改。没有新原生平台准入。

## 工具

- scripts/install_browser_archives.py：Windows 官方缓存回退；检查 ZIP 原始长度/MD5、越界路径、布局和可执行文件，拒绝覆盖缓存，不伪造依赖验收。新增 4 项测试通过。
- scripts/relocate_font_identity.py：只允许文件 SHA256 完全相同的路径迁移，保留身份与原始证据绑定。新增 4 项测试通过。
- scripts/doctor.py / scripts/run_checks.py 与旧字体探针测试增加显式 `--font-identity` / `UI_DESIGN_FONT_IDENTITY` 配置；完整 runtime 前检查字体文件哈希。
- tests/runtime-replay.test.mjs：4 项通过，检查原始截图差异、失败提取及输出范围。

## 产物

artifacts/task-023/browser-install.json、replay-final/replay_report.json、replay-final/{first,second}、runtime-relocated/{environment.json,checks.json,tests.log}、core-final/{environment.json,checks.json,tests.log}。

字体二进制未进入仓库；下载 ZIP、同字节字体路径记录和真实运行产物仅留本机 artifacts。此任务没有对外发布来源证据包。源截图已观察，Button、Input、Select 均正常显示；这不替代原生平台 PNG 和保真门。

## 新字体选择

用户明确要求设计字体使用 Figma/Penpot 默认字体。新任务按 docs/FONT_POLICY.md 与 policies/font-selection-0.2.0.json 执行，不要求本地苹方安装/上传。当前同字节迁移工具和测试结果仅保留作历史复验；实际平台默认字体绑定、重新测量和新组件准入是下一任务。
