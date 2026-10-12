# 可移植证据包契约 0.1.0

本契约用于新证据包的自包含文件运输与完整性检查。历史 0.2.1/0.3.0 manifest 和发布加载器不迁移、不改写、不绕过。新工具不会把旧 Missing 变为 PASS，也不将文件完整性认定为平台保真或组件准入。

Schema：`scripts/evidence-package.schema.json`。放在开发工具目录，避免新增 Schema 改变 V0.1 的 Core/Schema/Validator 程序指纹。

## 包结构

包根包含 `manifest.json` 与显式列出的 payload。Manifest 不包含源工作区绝对路径、账户文件引用或外部文件依赖。路径统一为可移植的相对 POSIX 路径；禁止反斜杠、空段、`.`、`..`、Windows 设备名、尾点、符号链接、大小写冲突和文件/目录冲突。

| 字段 | 含义 |
|---|---|
| scope / contractVersion | 固定为 portable-evidence-package / 0.1.0 |
| packageId / releaseVersion | 新证据包身份及其发布版本；不得借此冒充历史批准 |
| purpose | development 或 native-acceptance |
| versions | 显式版本锁；native-acceptance 要求现有九项流水线版本键全部存在 |
| artifacts | 文件 ID、包内路径、角色、原始 SHA256、字节数和分发声明 |
| coverage | 配置 ID、逻辑组件 ID、静态配置 ID、目标平台集合 |
| evidenceSets | 每个配置/平台的证据角色到 artifact ID 的映射 |

每个文件必须声明 `distribution.status: redistributable` 和非空 `basis`。声明是打包者的责任，不是本工具作出的法律判断；公开可见不是分发许可。字体优先保存合法来源与身份/哈希证据，专有字体二进制及账号截图不能因打包而获得分发权。工具不自动扫描或清除秘密，应先选择可分享的真实证据文件。

native-acceptance 每个配置/平台要求 source、component-ir、registry、tokens、rules、program、license、font-identity、ui-ir、execution、readback、native-png、visual-review、fidelity 十四个角色。引用必须存在且角色匹配；所有声明的平台都需要对应 evidenceSet。暂不定义组件状态/尺寸默认覆盖，不扩大已有准入范围。

**角色齐全和哈希一致仍不证明证据内容真实、PNG 有效、实例关联、字体身份、来源尺寸或视觉保真。** 这些语义由对应 Adapter 和验收器独立检查。本工具所有成功报告仍是 `nativeAcceptance: NOT_RUN`、`nativeExecution: NOT_RUN`、`releaseReady: false`。

## 打包计划

计划沿用 manifest 顶层字段。每个 artifact 使用 `source` 指定来源根目录内的相对路径，省略 sha256 和 bytes。包内路径由 `path` 指定；工具读取实际来源字节计算哈希和大小，最终 manifest 不保留 source。

最小开发包计划：

```json
{
  "scope": "portable-evidence-package",
  "contractVersion": "0.1.0",
  "packageId": "development-checks",
  "releaseVersion": "development-only",
  "purpose": "development",
  "versions": {"evidence_contract": "0.1.0"},
  "coverage": [],
  "evidenceSets": [],
  "artifacts": [{
    "id": "test-log",
    "source": "tests.log",
    "path": "evidence/tests.log",
    "role": "diagnostic",
    "distribution": {"status": "redistributable", "basis": "本任务生成的可分享测试记录"}
  }]
}
```

这是计划格式示例，不是实际成功记录。准备真实文件与明确分发依据后执行：

```powershell
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/evidence_package.py build --plan artifacts/new-evidence/plan.json --source-root artifacts/new-evidence --output-dir artifacts/new-evidence-package --report artifacts/new-evidence-build.json
rtk proxy .\.venv\Scripts\python.exe -X utf8 scripts/evidence_package.py verify artifacts/new-evidence-package --report artifacts/new-evidence-verify.json
```

build 仅允许新的 artifacts 子目录，拒绝覆盖已有包。前置检查聚合全部问题；检查通过后在独立临时目录写入，复验完整文件清单，再重命名为最终目录。失败不留下可误用的部分包。每个文件保持原始字节，禁止换行规范化或图像转换。

verify 可读取复制到任意位置的包，不读取原来源目录。会检查 Schema、ID 与覆盖关系、文件路径、大小、哈希、缺项、符号链接和未列出的附带文件。它不修改包。报告须放在包外的 artifacts 路径，避免报告成为未声明 payload。

退出码：完整性 PASS 为 0；MISSING/FAIL 为 1；参数错误为 2。JSON 重复键、非有限数值、未知字段和自报成功字段均不能进入契约。

## 后续原生接入

本增量交付打包契约、字节验证与开发日志包验证，没有产生新正式组件库或原生准入。后续需要为选定配置收集真实官方提取、合法字体证据、版本锁、目标文件实际执行、独立读取、原生 PNG、视觉复核和保真结果，并由新版本验收器核验内容及其相互绑定。仅工具报告 PASS 不得让正式 Registry 接纳组件。
