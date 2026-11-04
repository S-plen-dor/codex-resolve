---
name: resolve-edit
description: Help Codex edit video in DaVinci Resolve using natural-language intent, optional reusable tools, and editable projects.
---

# Resolve Edit

由当前用户的意图和实际素材决定剪辑。自主选择镜头、节奏、声音、效果和实现方式；未指定的创作细节可自行判断。这里不规定风格、工作阶段、提案数量或审批步骤。

工具按需使用：可以调用本工具包、官方 Resolve/Fusion API、可用的连接工具、FFmpeg、其他 Skills，或编写项目专用脚本。现有命令和示例不是创作边界；不必为了使用本 Skill 将所有任务转换为计划 JSON 或执行完整工具链。

需要查工具时看 [调用参考](references/workflow.md)；选择使用本包的计划执行器时，再按需查 [计划接口](references/plan-contract.md)。没有强制阅读顺序；已有上下文足够时直接工作。

执行时保留这些约定：

- 操作明确的目标工程，保护原素材和已认可版本，保留适合本次修改的恢复依据。
- 本包内部帧区间为零起点 [start,end)，帧率为有理数；对接其他接口时转换其时间约定。
- 如实区分创作意图、实际执行和观察范围。本包首个公开版本尚未运行验证；某个工具未实现，不代表这种剪法不允许。

需要跨对话续接时，可用 --workspace/resume 自动记录，也可采用适合当前项目的交接方式。交付说明结果位置及实际限制；普通剪辑决定不逐项询问用户。
