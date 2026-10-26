# TASK-155 官方组合方法接入Skill

用户批准：依据TASK-154学习结果调整Skill，保留完整Tree、灵活组合、官方组件与一次集中验收。不修改已有交付页面，不增加验收轮次或自写组件视觉CSS。

## 实施

- 新增`docs/IVIEW_COMPOSITION_PATTERNS.md`，保存四个官方在线示例的组合观察、适用范围与实现来源边界。运行观察日期2026-10-26；本机学习截图见`artifacts/task-154/adminplus-study/`。专用Admin Plus布局层未取得源码/版本一致性证明，不冒称本地基础包可直接复用整页实现。
- 主入口、快速入口、组合契约及官方依据说明统一为布局前选适用区域组合，在现有观察/关系证据中简记选择，完整Tree落实背景拥有者、边界、宽度、归属及组件变体/槽位。没有新增输入Schema、方案文件、业务模板或检查阶段。
- 去掉由组件名推导的强制居中：Core的壳组合继续要求背景与边界契约；浏览器Card extra继续检查容纳和分隔线，不因中心差本身自动失败。保留中心差诊断及显式`vertical-center`的严格检查；顶/基线等对齐在现有视觉复核中判断。1px只用于已有几何关系舍入。
- 不修改TASK-153历史记录和TASK-152页面，不把旧视觉问题改为已解决；本次仅纠正无来源的普遍居中假设，不证明其余布局已正确。

## 验证

- `node --test tests/html-layout-relations.test.mjs`：2项通过。覆盖断裂背景、错位边界、工具栏越界、容器内非居中不误报，以及显式居中关系仍拒绝错位；历史页面文件字节不变。
- `.venv/Scripts/python.exe -X utf8 -m unittest discover -s tests -p test_html_composition.py`：6项通过。背景/边界仍必需，居中可选，完整关系保留并拒绝缺失节点；官方样式覆盖及来源遗漏仍拒绝。
- skill-creator `quick_validate.py .`通过；最终diff空白检查通过。

当前完成的是Skill说明与相关通用检查调整；未运行新原型端到端生成，不宣称页面质量或5分钟目标已通过新实测。没有推送GitHub或改动全局安装Skill。
