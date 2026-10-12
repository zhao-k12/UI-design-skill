# TASK-021 — 开发预检与测试分组

日期：2026-10-12。范围授权：用户在项目检查和首个开发任务建议后要求“继续”。

## 范围与依赖

新增开发工具，不修改 Core 主链路、Adapter 执行、正式 Registry、package.json、来源锁或历史 manifest。复用 Python 标准库、现有 Node 依赖、官方 verifySource 和历史发布文件清单。V0.2 页面能力、原型假设和 Canvas 政策未在本任务实现。

## 交付

- scripts/doctor.py：结构化环境诊断、全部 manifest 缺项/改字节/越界路径报告、官方参考产物与来源/renderer 绑定。
- scripts/environment.mjs：Node/npm 版本、锁定 Chromium 与 headless shell 路径、完整官方来源锁检查；不下载或启动浏览器。
- scripts/run_checks.py：core/runtime/historical 测试路由；环境门不通过时保存 NOT_RUN；运行前使旧成功失效，保存日志、退出码和报告。
- tests/test_doctor.py：10 项边界测试，覆盖缺项聚合、路径越界、原始字节差异、非法 manifest、参考 renderer/截图变化、部分产物、分组路由和旧成功失效。
- docs/DEVELOPMENT_CHECKS.md 与 README 入口：命令、状态、外部前提及能力限制。

## 实际验证

命令均从仓库根目录执行，使用 rtk 前缀。Python 3.11.9、Node 24.15.0。

| 检查 | 结果 |
|---|---|
| 新诊断测试 | 10 项 PASS |
| scripts/run_checks.py --group core | 114 项 PASS，40.436 秒；测试与日志见 artifacts/task-021/core |
| scripts/run_checks.py --group runtime | MISSING，tests NOT_RUN；缺少 Chromium 1243、headless shell 和默认官方参考 |
| scripts/run_checks.py --group historical | FAIL，tests NOT_RUN；证据不足且存在字节哈希变化 |
| scripts/doctor.py --group native | FAIL；仍保留 live-platform-and-fonts NOT_RUN |
| scripts/environment.mjs 语法检查 | PASS |
| 官方完整来源锁 | PASS；package.json 与 lockfile 未改动 |
| git diff --check | PASS |

历史 manifest 共检查 430 个条目（不表示 430 个唯一文件）。0.2.1 列出 6 个缺项及 requirements-native-qa.txt 原始字节哈希变化；0.3.0 列出 5 个缺项。另缺少诊断依赖 Brotli 1.1.0。requirements-native-qa.txt 在本任务中未修改，不以规范化换行或改 manifest 消除差异。所有缺项/变化见 artifacts/task-021/historical/environment.json。

本次没有重新运行 Node 浏览器测试、完整 Python 历史字体测试或实际平台验收。预检故意阻止不满足前提的测试，未将其标记为 PASS。报告固定 nativeExecution NOT_RUN、releaseReady false。historical 环境预检不覆盖全部指定字体/FreeType/平台前提，详情见开发检查说明。

## 后续

本任务完成开发准备工具。下一增量优先为新版本建立可移植证据包契约及明确的配置覆盖范围，不跳过现有哈希或伪造历史文件。Canvas、模拟数据与语义批准迁移仍按 V0.2 计划记录待决策事项。
