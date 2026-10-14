# TASK-050 — 默认字体自由文字测量采集

日期：2026-10-14。状态：PARTIAL；V0.2 完整流水线仍 BLOCKED。架构冲突与建议见 [TASK-050_ARCHITECTURE_CONFLICT.md](TASK-050_ARCHITECTURE_CONFLICT.md)。

范围：V0.1 原型中的 12 个自由文字节点，使用 V0.2 Token 的字号与行高；不修改已准入组件、V0.1 输入锁或 Core 主链路。

Figma 文件 `0vGWSRoLxBiVPXiZ8xJAX9` 新建独立测量页 `169:2`，使用 Inter Regular 400、自适应宽高文本节点。创建后再次独立读取原生节点，12 项文案、字体、字号、行高、节点尺寸均记录于 `artifacts/task-050/figma-native-read.json`。`list.count` 读回宽 73 px，V0.1 捕获为 71 px；因此旧输入不能直接复用。

Penpot 目标文件仍为 `57949053-620f-8001-8008-c804c8d61529`。插件本轮返回 `No Penpot instance connected for user token`，浏览器唤醒也超时。原生写入和独立读回均未执行；可复用的测量脚本保存在 `artifacts/task-050/penpot-measure.js`，待插件连接后执行。Penpot 捕获、两端包络、组合单元测量、V0.2 独立输入及完整页面验收均未通过。

验证：本地证据校验检查 Figma 行集合、固定文案、默认字体参数及旧版尺寸差异；其结果不替代 Penpot 原生验收。
