---
name: resolve-edit
description: Use natural-language requests to analyze video, plan and revise edits, and operate DaVinci Resolve 21 with an installed Codex Resolve toolkit. Supports single-camera, multicamera and music-driven edits; preserves editable projects and versioned decisions.
---

# Resolve Edit

用户通过与 Codex 对话完成剪辑。技术计划由你维护，不要求用户填写 JSON 或逐镜头决定。先定位已安装的 codex-resolve / cr-media 命令或仓库虚拟环境；缺失时说明需要安装，不默认依赖某个 MCP 或个人目录。

首先读取 [workflow.md](references/workflow.md)。当前发行版是未运行验证的开发预览：媒体工具和 Fusion helper 已提供，通用建片、增量修改、渲染执行器未实现。使用实际可用的官方 API、脚本桥或连接工具执行，不编造命令与成功结果。

- 读取当前项目 HANDOFF.md、project.json、state.json；按需看分析和选中的计划，不扫描历史目录或模型库。
- 用户授权剪辑后自主完成素材分析、镜头安排、普通构图和效果取舍，先给可观看结果再迭代。若用户只要求讨论，保持只读。
- 需求不明时先完成独立分析，只询问实质影响结果且无法推断的信息。无法唯一定位修改对象时确认指代。
- 保护原素材、已认可版本和用户正在编辑的工程。修改前核对目标工程与工作时间线，保留恢复依据。项目记录检查点不等于工程备份。
- 内部帧零起点、区间 [start,end)、有理帧率；核对实际素材时基、入轨长度和源绑定。
- 不将频谱峰当确认重拍、相关偏移零当口型正确、解码通过当审片通过。视觉与技术检查分开报告。
- 主音轨策略按项目确定；需要连续原声时不得因切镜或慢放切碎或重复叠加。检查声道与增益。
- 用户要求跳过检查时记录 skipped，不因此虚构通过；软件或接口不支持时说明实际限制。
- Motion、Design 为可选外部能力，安装后遵循其适用流程。缺失时继续基础剪辑，调整视觉方案需说明。

每次阶段结束更新当前计划、工程/时间线、预览位置、已接受决定、问题和下一步。交付视频、可编辑工程位置与真实检查范围。
