# TASK-050 — 默认字体自由文字测量采集

日期：2026-10-14。状态：自由文字包络 PASS，组合单元和完整 V0.2 流水线仍 BLOCKED。架构决策见 [TASK-050_ARCHITECTURE_CONFLICT.md](TASK-050_ARCHITECTURE_CONFLICT.md)。

范围：V0.1 原型中的 12 个自由文字节点，使用 V0.2 Token 的字号与行高；不修改已准入组件、V0.1 输入锁或 Core 主链路。

Figma 文件 `0vGWSRoLxBiVPXiZ8xJAX9` 新建独立测量页 `169:2`，使用 Inter Regular 400、自适应宽高文本节点。创建后再次独立读取原生节点，12 项文案、字体、字号、行高、节点尺寸均记录于 `artifacts/task-050/figma-native-read.json`。`list.count` 读回宽 73 px，V0.1 捕获为 71 px；因此旧输入不能直接复用。

Penpot 目标文件 `57949053-620f-8001-8008-c804c8d61529` 的插件已重新连接。独立测量页 `f1153c87-a7fc-80d8-8008-c98abc1a1948` 使用 Source Sans Pro regular 400、自适应宽度文字。首次通过 PowerShell 传输脚本时中文发生编码错误；已用 Unicode 安全传输修正。Penpot 布局刷新后两次独立读回完全一致，12 项记录于 `artifacts/task-050/penpot-native-read.json`。其中 `list.count` 宽 69 px。

用户明确批准双端较大值政策。`artifacts/task-050/build_text_envelope.py` 以两个来源文件的 SHA-256 锁定输入，验证文案、字体、字号、行高、唯一 ID，再逐项取较大宽高。`artifacts/task-050/text-envelope.json` 的 `list.count` 宽 73 px；所有其他 11 项两端尺寸一致。包络只覆盖自由文字，未把自然宽度冒充字段、工具栏或表格组合单元的尺寸。

验证：两次独立 Penpot 读回一致；本地校验检查 Figma 旧版文案映射、两端字体与排版、包络可复算性，并用篡改文案负例确认拒绝错误输入。组合单元测量、V0.2 独立输入与最终页面验收尚未执行。
