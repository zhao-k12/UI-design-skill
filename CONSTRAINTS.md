# V0.1 Constraints

以下为用户 BUILD PLAN 的架构基线，未经明确架构决策不得改动。

1. AI 不得直接生成最终 UI。必须经过理解、结构、布局、组件映射、UI-IR、Adapter。
2. Core 不得直接依赖 Figma/Penpot API、SDK、Node/Object Model 或 Adapter 实现。
3. 所有平台输出必须经过 UI-IR；平台 ID 和实际组件引用仅在 Adapter Metadata 中保存。
4. 官方组件禁止 AI 视觉复刻。视觉真值来自官方源码、官方 CSS 和真实浏览器运行结果；只有 Fidelity Gate PASS 的设计组件可以进入正式 Registry。
5. 未登记组件禁止临时创建。优先区块、组合、基础组件，再由已有组件组合，否则记录 Missing Component。
6. 所有阶段必须保存结构化产物、QA 和 Checkpoint，禁止仅保存在 LLM 上下文。
7. 当前项目只处理静态页面。
8. 功能图标必须来自官方 Remix Icon 源码同步后的真实图标组件；不得自行绘制。
9. 缺失、未知和不支持必须显式记录 missing_component、missing_icon、missing_asset、unsupported_component 或 Review；不得猜造、静默替换或改变结构。
10. Layout Engine 按固定规则执行 24 Grid、Stack、Fill/Hug/Fixed 等布局；Adapter 仅翻译 UI-IR，不做设计决策。
11. 结构 QA 未通过不得进入布局；其他质量门未通过不得继续其依赖阶段。未执行检查不算 PASS。
12. 任务 manifest 锁定 Skill、UI-IR、组件库及源码、Remix Icon、Tokens、规则、两个 Adapter 版本；中途变更必须显式 Migration。
13. 支持阶段恢复和 Section 局部重建，禁止默认因小错误从头重跑。
14. 不提前开发 Design Brain、长期学习、RAG、自动规范修改、交互、动画、业务逻辑、代码生成、完整响应式、全部 ViewUI 组件或全部图标中文标注。
15. 每个开发任务必须读取架构、约束和开发状态，确认依赖、限定范围、测试、验收、记录、更新状态、Commit。
16. 架构问题先记录 ARCHITECTURE_CONFLICT 及当前设计、原因、影响、建议；不得自行重构主链路。

架构检查提供可执行的初始防线，不等于以上全部约束均已自动化验证。
