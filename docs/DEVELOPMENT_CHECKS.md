# 开发环境与分组检查

这些工具属于 V0.2 开发准备，不改变 V0.1 来源锁、正式 Registry 或原生质量门。检查工具只读环境与证据；仅在显式指定 artifacts 路径时保存新报告。不会安装依赖、启动浏览器、连接平台、修补哈希或补造证据。

## 环境诊断

在仓库根目录使用项目 Python：

```powershell
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/doctor.py --group core --output artifacts/checks/core-environment.json
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/doctor.py --group runtime --output artifacts/checks/runtime-environment.json
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/doctor.py --group historical --output artifacts/checks/historical-environment.json
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/doctor.py --group native --output artifacts/checks/native-environment.json
```

不传 `--output` 时只输出 JSON。可通过 `--node` 指定 Node 可执行文件。Python 依赖按 requirements 的显式 pin 核对；Node 依赖按 package.json 核对，另外执行官方完整 source lock 校验。不会增加 npm scripts，因为 package.json 本身属于冻结来源锁。

| 组 | 诊断范围 | 测试入口 |
|---|---|---|
| core | Python 3.11+ 与开发依赖版本 | 原基础 82 项、原型/结构/流水线 22 项、诊断与可移植证据包测试 |
| runtime | core 前提、Node 24+、npm 包、来源锁、两个 Chromium 可执行文件、Windows host 测试用 .venv、官方默认提取参考 | 全部 tests/*.test.mjs，以显式文件列表运行 |
| historical | Python 开发/诊断依赖、0.2.1 与 0.3.0 manifest 全部文件路径和原始字节哈希 | Python unittest discover 全套历史测试；包含 core |
| native | runtime 与 historical 前提，以及 live-platform-and-fonts: NOT_RUN | 不提供自动原生执行；在实际会话按原 Adapter/Release Gate 工作流验收 |

historical 的 manifest 诊断列出全部缺失、改字节或越界文件，不只返回第一个错误。0.3.0 加载器依赖 0.2.1，所以同时报告两份证据。完整 historical 测试还可能依赖诊断没有覆盖的指定字体、固定 FreeType、其他历史文件和 runtime 产物；预检 PASS 只是必要前提，最终以实际测试结果为准。

浏览器检查只确认锁定安装路径上的可执行文件存在。不会把旧浏览器当成新版本，也不会据存在性宣称浏览器可启动。runtime 参考检查包含提取状态、IR/manifest、截图/画廊哈希，以及当前来源锁和 renderer 绑定；不等于组件原生保真准入。

## 运行检查并保存结果

```powershell
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/run_checks.py --group core --output-dir artifacts/checks/core
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/run_checks.py --group runtime --output-dir artifacts/checks/runtime
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/run_checks.py --group historical --output-dir artifacts/checks/historical
```

输出目录包含 `environment.json`、`checks.json`，实际运行测试时另存 `tests.log`。任何未满足前提都会阻止测试并保存 `tests: NOT_RUN`。重跑前先使旧 checks.json 成功状态失效；以 checks.json 为当前结果，历史 tests.log 不可替代本次未执行状态。实际测试退出码非零则记录 FAIL；中断记录 PARTIAL。

`native` 组总保留实际会话检查 NOT_RUN，因此命令不能给出原生 PASS。所有报告固定 `nativeExecution: NOT_RUN` 和 `releaseReady: false`。

## 状态与退出码

- PASS：本组已检查前提或实际运行的测试通过，不表示发布就绪。
- MISSING：依赖、浏览器、产物或 manifest 绑定文件不可用。
- FAIL：版本不匹配、哈希变化、非法 manifest/路径、探针错误或实际测试失败。
- NOT_RUN：原生会话验收未执行；不得折算为 PASS。

汇总优先级为 FAIL、MISSING、NOT_RUN、PASS。成功退出 0；其余退出 1。参数错误由 argparse 返回 2。细项报告保留所有问题和各自状态，避免汇总掩盖缺项。

当前公开快照缺少账号界面截图与部分历史决定，不能通过跳过检查、修改历史 manifest 或伪造文件解决。应为新版本建立可分发的新证据包；保留旧版原始字节。
