# 官方 runtime 复验

默认 fixture 是已锁定 View UI Plus 1.3.24 的 Button、Input、Select。复验只执行真实浏览器提取，不重定义组件源码、CSS、字体或原生准入。

```powershell
rtk proxy npx playwright install chromium
rtk proxy node scripts/runtime_replay.mjs --output-dir artifacts/new-task/replay
```

输出必须是新 artifacts 子目录；已有目录即拒绝，不覆盖先前成功或失败。first 与 second 各自保存完整原始产物。replay_report.json 检查组件数据、环境、提取报告、manifest、三份截图和画廊的精确字节，且实际浏览器版本须与锁定 Playwright metadata 相同。不使用截图转换、遮罩或容差。

为现有测试准备参考：README 的官方 extractor 可写入 artifacts/task-006。也可在该目录不存在时将实际成功 first 目录按原字节复制过去。本机 TASK-023 使用后一方式。

完整 runtime 测试仍含历史字体文件探针。它的字体文件必须与已保存身份 SHA256 相同。仅文件位置不同可以生成新的本地路径记录：

```powershell
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/relocate_font_identity.py --identity adapters/figma/metadata/font-file-identity.json --family "PingFang SC" --font "实际相同字节的本机字体路径" --output artifacts/new-task/font-identity.json
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/run_checks.py --group runtime --font-identity artifacts/new-task/font-identity.json --output-dir artifacts/new-task/runtime
```

如果没有合法的相同文件，检查返回 MISSING 或 FAIL；不下载或替换专有字体。这是历史诊断前提，新设计字体按 FONT_POLICY.md 使用平台默认字体。

## Windows 下载回退

标准下载器网络失败时，可通过 TLS 从 Chrome for Testing 官方 bucket 获取当前 Playwright browsers.json 指定的浏览器版本。TASK-023 的锁定版本是 153.0.8010.12，后续版本变更须重新核对 metadata，不能复用这些 URL 冒充新版本。

```powershell
rtk proxy curl.exe -f -L -D artifacts/new-task/downloads/alternate-chromium.headers -o artifacts/new-task/downloads/alternate-chromium.zip https://chrome-for-testing-public.storage.googleapis.com/153.0.8010.12/win64/chrome-win64.zip
rtk proxy curl.exe -f -L -D artifacts/new-task/downloads/alternate-headless.headers -o artifacts/new-task/downloads/alternate-headless.zip https://chrome-for-testing-public.storage.googleapis.com/153.0.8010.12/win64/chrome-headless-shell-win64.zip
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/install_browser_archives.py --downloads-dir artifacts/new-task/downloads --report artifacts/new-task/browser-install.json
rtk proxy npx playwright install chromium
```

先创建上述 downloads 目录。回退读取真实 TLS 下载保存的官方 HTTP 200 长度/MD5响应，校验 ZIP 字节与安全路径，再建立新的默认 Windows 浏览器缓存目录；不覆盖已安装版本。MD5用于传输完整性，不是发布者签名；报告另保存 SHA256。工具不下载文件，既有缓存无需再次运行回退，标准 Playwright installer 负责依赖检查。

报告保留 nativeAcceptance/nativeExecution NOT_RUN 和 releaseReady false。可重放来源测量通过不等于 Figma/Penpot 组件准入。
