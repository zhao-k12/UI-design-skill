# Learnings

## [LRN-20261108-001] correction

**Logged**: 2026-11-08
**Priority**: high
**Status**: resolved
**Area**: frontend

### Summary
UI 页面生成必须在首次渲染前完成组件、图标、提示文字和分页策略的强制检查，并对同一任务复用固定交付页。

### Details
本轮反馈暴露了五类重复问题：表单图标/placeholder 缺失、Tabs 语义被替换成其他组件、默认分页被原型分页状态覆盖、导入/导出/新增等按钮漏图标，以及每次调整都向用户暴露新的 run HTML。内部渲染记录可以保留，但用户交付应固定覆盖任务根目录的 page.html。

### Suggested Action
将上述规则写入 ui-design-skill 的不可降级质量门和独立复扫清单；对工具栏按钮执行 icon completeness 检查；未明确分页时强制使用默认分页；render/revise 只更新内部 run，finalize 后统一发布固定 page.html。

### Metadata
- Source: user_feedback
- Related Files: C:/Users/38442/.codex/skills/ui-design-skill/SKILL.md
- Pattern-Key: harden.ui-output-quality

### Resolution
- **Resolved**: 2026-11-08
- **Notes**: 已更新项目版及已安装版 skill 规则。

---
