# Remix Icon Manager V0.1

只同步官方发布包中的原始 SVG 与锁定提交的 tags.json；不绘制图标。版本检查不会升级。此阶段输出的是 source-ready 图标来源 Registry 与原生组件增量计划；Figma/Penpot 实际组件创建、更新和对象验证由后续 Adapter 执行。

```powershell
.venv/Scripts/python.exe -X utf8 -m icon-manager.remix-sync check
.venv/Scripts/python.exe -X utf8 -m icon-manager.remix-sync sync --version 4.9.1
.venv/Scripts/python.exe -X utf8 -m icon-manager.remix-sync verify
.venv/Scripts/python.exe -X utf8 -m icon-manager.remix-sync search 搜索
node icon-manager/remix-sync/preview.mjs
```

同步必须指定版本，禁止 latest。已登记源锁改变时须显式添加 `--migration`；不会修改 TASK-006 的 npm 依赖。新运行中的流程不应自动切换旧锁，完整任务 Migration/Checkpoint 仍由 TASK-017 实现。网络或校验失败报告 FAIL，不使用 master 或其他图标库兜底。

来源为 [官方 Remix Icon 仓库](https://github.com/Remix-Design/RemixIcon) 与官方 remixicon npm 包。锁包含版本、Git Commit、发布包 SHA512 SRI/SHA256、npm 元数据哈希、官方标签哈希、许可证哈希及 SVG 总清单哈希；实际下载证据保存在 artifacts/task-008/source。官网标签按类别与基础名称匹配，line/fill 共享其官方标签；没有后缀的官方 Editor 图标保存为 neutral，不凭空创建变体。

source-lock 的 license 字段原样记录 package.json 声明：该发布包声明 Apache-2.0，但实际随包 License 文档标题为 Remix Icon License v1.0。已保存真实文档及哈希，元数据字段不能替代 License 原文。

## 不可变存储与增量

registries/icons/current.json 只指向 SHA256 命名的不可变快照。快照包含 registry.json、source-lock.json、custom-tags.json、semantic-index.json、原始 License 和 manifest.json。原始 SVG 按内容哈希存于 objects；Git 禁止对 SVG/License 转换换行。离线 verify 检查快照文件、索引重建、所有当前/历史 SVG 哈希及有效 SVG XML。

- 同名同 SVG 哈希：unchanged，不计划平台图形写入。
- 同名不同哈希：update，保留逻辑 ID 并保存历史版本；后续 Adapter 原位更新其 Metadata 对应的实际组件。
- 新增：create；后续 Adapter 创建原生图标组件。
- 删除：deprecate，保留 Registry 项、旧快照、所有旧 SVG，不删除历史对象。
- 重新出现：reactivate；若图形也变化，同时记录 update。
- 仅标签改变：reindex，不产生 SVG update。

校验所有字节后原子切换 current.json，之前的快照不覆盖。中断或失败可能留下未引用的内容对象/快照，不会清理历史资源。同步结果与 incremental_diff.json 保存到 artifacts/task-008，nativePlatformApplication=NOT_RUN，不能把计划当作平台实际应用。

## 语义与缺失

Core 的 IconRegistry 只读平台无关逻辑描述与哈希，平台 ID 不进入 Registry。resolve 未登记 ID 抛 missing_icon；deprecated 图标默认拒绝新引用，历史读取须显式 historical=True。实际旧页面还应锁定旧快照和 SVG 哈希，而非自动采用新的同名图形。

索引由官方标签、官方名字词及独立 custom-tags.json 组成。中文补充只覆盖五种明确项目语义：搜索→search-line、删除→delete-bin-line、新增→add-line、导出→download-line、设置→settings-3-line。没有修改官方标签或图形；不是对全部图标添加 AI 中文推测。

查询使用精确词匹配，权重 custom=1、official=0.85、name=0.75，按查询词覆盖率计算置信度；阈值 0.8。默认 line，可显式 fill/neutral，不悄悄换样式。未知、低置信度或同分歧义均返回 no_icon 与候选/原因。此固定规则未做真实用户检索效果评估，也没有 LLM、长期学习或模糊语义猜测。

内存 test-fixture 默认被 Core 拒绝，不能 publish。测试中的临时存储模拟仅验证事务/历史机制；正式快照来自实际官方发布提取。浏览器预览展示源 SVG，仍不等于平台原生实例验收。
