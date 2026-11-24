
## 6.43 · 2026-11-24 台上那十分钟删「崩着上台」门槛（用户拍板）

- cond 简化为：季末舞台 <72、心理 <35（played_while_collapsing 条件删去；旗标写入保留在引擎里但不再被任何结局引用）。lore/攻略措辞同步。
- 复扫 2400 局分布几乎不变（台上 2——脚本玩家心理很少低于 35，真人暗线打法易达）；trace/loop 无需重录全对；validate_all 八组 0；tsc 0；build 过。
## 6.44 · 2026-11-24 开屏更新日志（用户拍板）

- 序章三张 text 屏带 intro:true（py/ts 双侧，基准重录 loop 74781 项——intro 标入轨），ui renderStep 按 step.intro 在 #stage 顶部注入「✦ 这次更新了什么」小签，立档后自动撤。
- 检测演进：先试 payload intro:!g.state（序章屏 state 已存在，判不出）→ 再试 !snap（同因）→ 定稿 step.intro 数据标。快速重开走 renderStep 直调不走 refresh，所以注入必须放 renderStep 本体。
- 日志内容内联在 ui.js CHANGELOG 常量（vite publicDir=web/sprites，fetch 数据文件 404）：2026.11.21 网站出生了；2026.11.24 三条（bug 修复/存档系统十档/兜底结局参数优化 详见攻略◉‿◉，用户逐字）。面板复用 gal-panel 样式，Escape/遮罩可关。
- 预览截图确认两条渲染正确。
