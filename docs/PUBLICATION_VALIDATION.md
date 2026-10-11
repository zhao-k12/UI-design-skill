# Public snapshot validation

2026-10-11，Windows，Python3.11，Node24.15.0。

| 检查 | 结果 |
|---|---|
| Skill frontmatter / 命名验证 | PASS |
| Core架构边界静态检查 | PASS |
| Python平台无关基础测试 | 82项PASS，18.505秒 |
| Node完整测试 | 111项PASS，16.184秒 |
| 官方默认组件真实运行提取 | PASS，Button/Input/Select；不代表原生保真准入 |
| npm ci | 成功；audit报告0项漏洞 |
| 公开文件扫描 | 无匹配认证Token/私钥、账号邮箱、专有字体文件或排除的试验开发内容 |

Python基础测试范围：`tests.test_architecture`、`tests.test_ui_ir`、`tests.test_tokens`、`tests.test_layout`、`tests.test_layout_builder`、`tests.test_component_registry`。

初次Node运行缺少新目录的虚拟环境及`artifacts/task-006`，4项检查失败，未当作PASS。按README安装环境并实际重新提取官方参考后，完整111项复验通过；生成参考和依赖仍按.gitignore留在本机，不上传。

没有重新执行公开版全部Python字体/原生保真门，也没有在新平台文件中重新生成页面。固定FreeType、合法字体、平台权限、被排除的账号界面截图/原始决定等仍是某些历史门的本机前提。公开版不声称历史完整门可以直接重放，也不把本次文档发布当成V0.2完成。
