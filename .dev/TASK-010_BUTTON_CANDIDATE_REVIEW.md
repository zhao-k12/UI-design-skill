# TASK-010 首个原生组件候选

目标：仅在 `UI Design Skill — TASK-010 验收`（文件 91396aad-60c8-808b-8008-c0885ca79899）当前验收页面建立一个 Button 候选。插件代码校验实际文件和页面；已有同名候选即停止，不重复创建或删除旧内容。

内容直接来自已锁定官方 Component IR：60×32 主按钮，填充 #2d8cf0、原生内侧边框、圆角 4、可编辑文字“查询”，PingFang SC Regular 14px。source Component IR SHA-256 为 `66d8984b25e8e3e080e864396eaf25f168fd2cf9395a6111628ed9ca7036ed4f`。没有 Figma 节点或基线参数进入该候选。

建立过程调用 Penpot 原生 Board/Text/Library.createComponent，并保存精确创建记录。文字位置首先使用官方源的行框，基线仍 NOT_RUN，不把未验证字体测量宣称通过。独立读取实际原生属性及原生 PNG/SVG 后，还须测量、校准并通过 AD-017 完整保真检查；在此之前 admissionEligible=false，不登记正式 Penpot Registry 引用。

插件需要 content:write 和 library:write（自动包含对应读取权限）。Penpot 的权限范围包含用户有权访问的内容及库，但代码限定上述单个验收文件、单个官方源候选；不包含修改任意文件、删除、分享、评论、读取用户资料或外部上传操作。原生结果仅发到本机回环服务保存。

实现：[component_candidate.py](../adapters/penpot/component_candidate.py)、[component_candidate.js](../adapters/penpot/component_candidate.js)、[component_capture.js](../adapters/penpot/component_capture.js)、[host/server.py](../adapters/penpot/host/server.py)。执行计划保存于本机 artifacts/task-010/button-candidate-plan.json。首次安装写入插件必须在实际权限窗口获用户批准后继续。
