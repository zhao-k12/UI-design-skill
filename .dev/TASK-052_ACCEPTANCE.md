# TASK-052 — V0.2 完整页面双平台原生验收

日期：2026-10-14。范围状态：**PASS**（本次冻结用户管理列表页面）；V0.2 全覆盖发布门仍未验收。架构问题及限定修正见 [TASK-052_ARCHITECTURE_CONFLICT.md](TASK-052_ARCHITECTURE_CONFLICT.md)。

输入锁：TASK-051 最终 UI-IR SHA-256 `512b2f737222ac5e0209cf88a55ea4cd329e429eb339247e3990cd2ec84aa7b1`。Figma 和 Penpot 使用同一 UI-IR，Adapter 计划版本均为 `0.1.0`。新输入继承冻结原型语义和 V0.2 已准入组件、图标、双端字体包络；未覆盖 V0.1 历史文件。

原生目标：Figma 文件 `0vGWSRoLxBiVPXiZ8xJAX9`，页面 `172:2`，根框架 `173:2`；Penpot 文件 `57949053-620f-8001-8008-c804c8d61529`，页面 `f1153c87-a7fc-80d8-8008-c997a361507f`，根画板 `f1153c87-a7fc-80d8-8008-c997d2e66ff8`。两端均为 1920×1080，三个区块依次为 Header 1872×28、Query 1872×94、Table 1872×270。原生页面包含 12 个计划内自由文字、24 个总文字节点、四个官方组件真实实例和两个 Remix 图标真实实例。Figma 自由文字均为 Inter Regular；Penpot 均为 `sourcesanspro`。固定跨平台文字包络和全部文字内容读回一致。

首次 Penpot 写入在所有 93 个节点创建后因 `waitForLayoutUpdate` 超时被误报 `PARTIAL`；独立读回与原生 PNG 确认页面完整。该页改名为布局等待诊断页并保留，不作为正式结果。仅移除 Penpot 基础 Adapter 写入末尾的阻塞等待；新建独立验收页后返回 `EXECUTED`。原生写入与最终质量门仍分开。新页再次独立读回 93 个节点、24 段文字和六个实例；结构报告 [native-qa.json](../artifacts/task-052/native-qa.json) 为 `PASS`、`issues=[]`。

两端 1920×1080 原生 PNG 分别保存于 `artifacts/task-052/figma/native-page.png` 和 `artifacts/task-052/penpot/native-page.png`；原生读回 JSON 与 Penpot 执行账本也已保存。实际内容区域 `(0,0)–(1920,464)` 的平均 RGB 绝对差为 `0.684/0.650/0.597`（8-bit 通道）。两张整页图目视比较未发现内容遗漏、图标错位或可见文字裁切。正式发布仍须对新原型、覆盖矩阵、全部 Release Gate 和恢复流程另行验收；本次 PASS 只覆盖冻结列表页。

验证：`node --test tests/penpot-runtime.test.mjs` 19 项通过，新增布局等待超时回归；`python -m unittest tests.test_penpot_adapter -q` 6 项通过；`python scripts/validate_task052_native.py` 双端读回、PNG 尺寸和内容区域差异 PASS。预检与上游 Core 回归见 TASK-051。下一步盘点 V0.2 剩余 Release Gate；旧诊断页在确认无需保留后可清理。
