# Penpot Adapter — TASK-010 PASS

同一固定UI-IR已在真实Penpot文件生成34个逻辑节点和6个真实组件/图标实例，完整原生PNG1440×496。四类组件的完整独立保真和两份官方Remix图標的来源编码/边缘验收均通过。证据见metadata/list-acceptance/final-qa.json及项目.dev/TASK-010_ACCEPTANCE.md。

compiler执行前要求实际文件、精确字体、完整Penpot组件凭据及图标可重算Gate。runtime通过Board/Flex、原生Text和LibraryComponent.instance组装；未知资源和不支持的覆盖拒绝，不绘制替代品。

capture独立读取全树、实际布局/字体/内容、可见性/效果和原生PNG；保留原始堆叠顺序并明确反向布局顺序归一化。qa只判断结构，成功仍为REVIEW；page_final_qa另行检查实际位置、六实例、来源绑定、双平台逻辑结构及绑定原生PNG的视觉审查，才完成固定页验收。

page_recovery只处理精确已有记录中的默认透明度或公开resetOverrides操作，不detach、不删除或重复创建。page_instances保留格式失败；补导只复用同文件/revision和完全相同的节点/主节点状态，所有原始回执保留。

## 本地预检

```powershell
.venv/Scripts/python.exe -m adapters.penpot examples/adapter-fidelity-acceptance.ui-ir.json --file-reference 91396aad-60c8-808b-8008-c0885ca79899 --font-bindings adapters/penpot/metadata/font-bindings.json --icon-bindings adapters/penpot/metadata/icon-bindings.json --native-fidelity adapters/penpot/metadata/native-fidelity.json --output-dir artifacts/task-010/<新的空目录>
```

预检PASS不代表再次实际执行或验收。已有页面须使用保存的执行记录读取和恢复；不要重新创建。同一凭据只适用于已发现的指定验收文件。

四组件证据在metadata/native-fidelity.json；图标Gate在metadata/icons-native-v1/gate-report.json；完整页面、失败回执、原生PNG/SVG及SHA清单在metadata/list-acceptance。PDF只用于组件字形诊断，浏览器SVG重现仅为独立证明，均不替代原生生产PNG。

当前只支持固定尺寸的已准入静态组件。props/slots、实例视觉覆盖、Image、Divider、未验证阴影、任意响应式和交互仍拒绝或不在范围；完整项目Release Gate尚未通过。
