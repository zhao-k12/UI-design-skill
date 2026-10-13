# 平台默认字体预检

TASK-024 在用户指定文件实际创建临时原生 Text，先读取默认字体，再解析实际提供的 400/600 字重、导出中文与英文样张，最后删除自己的节点并检查顶层节点清单未变。探针只用于诊断，不是页面生成入口。

- Figma：Inter Regular / Semi Bold。首次脚本错误将非斜体样式限定为 REGULAR；修正后真实绑定通过。返回体超过工具限制的尝试已被平台回滚；后续使用原尺寸 PNG。
- Penpot：原生 family/id 为 sourcesanspro，400 为 regular，600 为 600；无需安装或上传本地字体。
- 中文样张不能证明中文实际字形来自这些西文字体；有效 CJK 字体身份保持 UNVERIFIED。
- Figma 正文在首次原生导出时缺少末尾“启用”，同一节点第二次连续导出显示完整；单独创建的正文节点复现了这一现象。探针先完成一次导出，再以第二次导出作为样张。保留首次失败与隔离诊断证据，最终正文及标题视觉检查 PASS。
- Penpot 两份 PNG 的中文和英文目视完整，文字样张检查 PASS。这只覆盖给定样本文字，不代表任意字形、组件或页面通过。

两个平台的探针代码位于 adapters/figma/default_font_probe_v02.js 和 adapters/penpot/default_font_probe_v02.js。当前目标的已验证绑定分别保存在 adapters/figma/metadata/default-font-target-0.2.0.json 与 adapters/penpot/metadata/default-font-target-0.2.0.json，包含来源证据 SHA256。主机必须先读对应平台 API 能力指南，再传入预期文件/page，不能自动切换到其他目标或从旧 metadata 照搬 ID。所有真实绑定和文件 ID 只存在 Adapter 配置与任务证据。

预检入口：

```powershell
rtk proxy .venv/Scripts/python.exe adapters/default_font_profile_v02.py --observation artifacts/task-024/figma/observation.json --review artifacts/task-024/figma/visual-review.json --platform figma --file 0vGWSRoLxBiVPXiZ8xJAX9 --page 0:1 --output artifacts/task-024/figma/profile.json
rtk proxy .venv/Scripts/python.exe adapters/default_font_profile_v02.py --observation artifacts/task-024/penpot/observation.json --review artifacts/task-024/penpot/visual-review.json --platform penpot --file 91396aad-60c8-808b-8008-c0885ca79899 --page 91396aad-60c8-808b-8008-c0885ca7989a --output artifacts/task-024/penpot/profile.json
```

预检检查目标身份、节点清理、原生字重绑定、样张几何、PNG 文件头及尺寸、视觉复核绑定的 PNG SHA256；PNG 文件头检查不是完整解码验收。输出锁定 observation、review 和政策 SHA256。输入失败先使旧输出失效；退出码 0 为样张 PASS，2 为需复核，1 为输入失败（rtk 可能将非零状态归一为 1）。视觉 review 是外部人工/代理观察证据，不是由预检程序自动判断画面。

fontBindingReady 只表示绑定可解析；readyForPageGeneration、componentMeasurementReady、releaseReady 始终 false。新字体下 Button/Input/Select/Table 仍需来源绑定的真实测量和独立原生 Fidelity Gate，不覆盖历史 Registry、Core、Tokens 或锁文件。最小覆盖计划见 policies/component-coverage-0.2.0.json。

真实 JSON、原生 PNG、visual-review、profile 和白底样张预览保存在 artifacts/task-024。预览由浏览器在白底显示原生透明 PNG，未替代原生导出。
