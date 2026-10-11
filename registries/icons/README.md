# Official Icon Registry

生产入口为 current.json；其 snapshotSha256 指向不可变 snapshots 目录。Core 只接收经过校验的 registry.json，不读平台对象引用。使用与版本迁移说明见 [Icon Manager](../../icon-manager/README.md)。

objects 保存未修改的官方 SVG；旧快照、deprecated 项及历史图形全部保留。source-ready 仅表示官方来源已锁定，不代表两个平台中已存在实际组件。五个 Figma 图标已有实际组件/实例及独立 Adapter Metadata；Penpot 与真实增量更新仍待验收。
