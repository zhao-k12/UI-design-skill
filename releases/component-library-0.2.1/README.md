# Component Library 0.2.1

TASK-019 发布：在已有组件基础上增加两份已冻结的官方 Table 正文。两列两行 720×96，四列四行 960×192；双平台完整原生保真、真实关联实例和视觉复核均通过。可编辑文字保留实际 Arial／苹方字体；每个配置拥有自己的来源摘要与逻辑 ID。

## 显式选择版本

```python
from adapters.component_library_versions import load

registry, bindings = load('0.2.1')
logical_id = 'data.table.config.4fe0393d9091c298f4469e4e95f43824af5373fe0552434be0ed2887e3857a72'
component = registry.resolve(logical_id)
figma_reference = bindings['figma'].resolve(logical_id)
penpot_reference = bindings['penpot'].resolve(logical_id)
```

另一份配置的逻辑 ID 为 `data.table.config.b3eb343b6ad2c8cd567a53f7d65703db6627cb9e7e1bfaedfb3098baf7af8122`。两份组件不声明可改写的 slot；不能用 props 或修改文字将其变成其他数据。新原型依然须经过语义复核、布局、映射、UI-IR 与实际 Adapter 验收。

版本目录保留独立、平台无关的 Core Registry 实现及原契约 schema。它仅为以上两份配置识别证据完整的 0.2.1 像素覆盖门；原有 0.2.0 准入规则保持原义。平台 ID、绑定、原生凭证都保存在 `adapters/*/metadata/component-library-0.2.1/`。`manifest.json` 绑定程序、来源、四份保真报告及实际实例证据；加载时逐文件检查。

旧 `registries/components/catalog.json`、Core 程序、TASK-017 运行目录和版本锁保持原字节。这里的选择不是自动升级旧任务；新任务应在 manifest 中锁定 `component_library_version=0.2.1`、Registry 指纹及此 release manifest 的摘要。

## Adapter 入口

Figma 使用现有 `adapters.figma.compiler.prepare` 和真实实例运行能力。Penpot 使用 `adapters.penpot.configurable_table_compiler.prepare`，传入本版本绑定及 `adapters/penpot/metadata/component-library-0.2.1/native-fidelity.json`；该入口以实际 Registry 类型验证新门，同时接受本版本保留的旧组件凭证。翻译 payload 的 ABI 仍为 0.1.0；未更改原生执行格式。旧入口和旧任务不自动改用此凭证。

这次实证是官方组件制造与真实实例验收。它不声称已经生成新的业务页面，也不扩展到表头、交互、任意列／数据改写、所有 Arial 字形或其他字体。当前新原型映射和内容契约仍须按现有规则逐项处理，不绕过 Unsupported。

## 验收重跑

需要已授权的本机原字体、requirements-native-qa.txt 及固定开发诊断依赖：

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-native-qa.txt
.venv/Scripts/python.exe -m pip install --no-deps --target artifacts/task-019/freetype-probe-deps freetype-py==2.5.1
.venv/Scripts/python.exe -m unittest tests.test_figma_configurable_table_fidelity tests.test_penpot_configurable_table_instances tests.test_component_library_versions
```

诊断拒绝与锁定 SHA 不一致的 FreeType 2.13.2 DLL、包装器或源字体。字体文件未提交到仓库。`scripts/admit_configurable_tables.py` 在全门与真实实例／视觉复核通过之后才写新 release；它拒绝覆盖已发布目录。历史失败、初始邮箱换行、画板重叠和导出超时回执仍保留。
