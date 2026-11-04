# 项目续接与反馈修订

0.1.0.dev2 新增实现，未运行测试。自然语言理解与审美判断由 Codex 进行；命令提供状态记录、定位和可靠保存新计划的机制，不是独立语言解析器。

## 明确项目作用域

先使用 init 创建项目。在需要自动跟踪的命令末尾添加 `--workspace PROJECT_DIRECTORY`。这是本机项目记录目录，与 plan-apply 的 `--project RESOLVE_PROJECT_NAME` 不同。未提供 --workspace 时保留原行为，不自动选择或写入任何项目。

支持跟踪observe、plan-revise、plan-apply、render-submit、render-status、produce、render-collect、review-record。使用 `plan-register PLAN --workspace PROJECT_DIRECTORY` 显式选中现有计划；plan-validate、plan-diff 和 plan-locate 保持只读，不改变当前版本。

```powershell
codex-resolve observe media/source.mp4 --out analysis/overview --workspace .
codex-resolve plan-register plans/v001.json --workspace .
codex-resolve plan-apply plans/v001.json --project MY_PROJECT --timeline WORK_V001 --out versions/build-v001 --save-current --workspace .
codex-resolve render-submit versions/build-v001/operation.json --out renders/preview-v001 --preset PREVIEW_PRESET --start --workspace .
codex-resolve render-status renders/preview-v001/render.json --workspace .
```

命令完成或失败后自动保存事件到 history/、原子替换 state.json，再生成 HANDOFF.auto.md。HANDOFF.md 与 creative-brief.md 留给 Codex 记录叙事、用户已认可内容和创作判断，不会被自动交接覆盖。命令不会自动推断 accepted_decisions 或修改源素材登记。

状态包含最新观察包、当前计划/指纹/版本、工作工程/时间线/操作记录、当前渲染记录、最新反馈、错误与下一步。失败时保留之前有效版本，并附失败记录位置。选中新计划后将原操作/渲染放到 previous_* 字段，清空当前指针并标记待构建；历史文件不删除。重新登记相同内容的计划不会无故作废已有关联。

旧操作的预览可以被提交，但不会冒充当前计划预览。渲染查询仅当记录是当前任务时推进阶段；Complete 标记为 render_complete_not_reviewed，不代表成片规格、感知或用户验收。当前可通过render-collect关联真实产物、review-record记录用户/agent的审片声明，但不自动认证实际感知过程。

## 新聊天继续

```powershell
codex-resolve resume PROJECT_DIRECTORY
```

resume 只读返回项目事实、状态、缺失的当前产物路径、当前计划是否被外部改动和锁状态。然后读取 HANDOFF.auto.md、HANDOFF.md、creative-brief.md，以及需要的计划/操作记录。它不连接 Resolve，不验证媒体哈希，也不自动恢复工程。使用 live Resolve 工具前仍需核对实际目标和用户任务。

## 将反馈落实到镜头

1. Codex 阅读用户原话、当前计划和实际预览。使用 `plan-locate PLAN --start FRAME [--end FRAME]` 找时间区间内的视频及音频 ID；帧区间属于输出时间线，不是源素材帧。
2. 结合 reason、构图、画面和上下文确认目标。“第二个特写”等语义指代由 Codex 判断；目标有歧义且会改错时再询问。
3. Codex 生成 changes JSON，记录原话、解释、基础计划 SHA-256、要保护的 ID 及具体操作。示例见 examples/changes.example.json；用户不需编写它。
4. 保存新的计划：

```powershell
codex-resolve plan-revise plans/v001.json --changes feedback/change-001.json --out plans/v002.json --revision v002 --workspace .
codex-resolve plan-diff plans/v001.json plans/v002.json
```

changes 支持 group=shots/audio，action=update/add/remove。update 的 set 替换对应字段的整个值；例如 properties 是整体替换，不是递归合并，需保留仍需要的旧属性。unset 仅删除可选字段。add 需完整 clip 与新 ID；remove 删除目标。每份变更对一个 ID 只执行一次操作。

不自动做 ripple：缩短镜头后是否留空、移动后续镜头或添加镜头，由 Codex 按创作意图明确列出；同轨重叠会被结构检查拒绝。preserve_ids 中的镜头内容必须保持不变。基础哈希或当前 workspace 计划不匹配时拒绝修订，避免旧反馈误改新版本。

命令在副本上修改，先写入同目录 draft 并做结构检查，再以新文件发布计划和 .revision.json 记录；不修改基础计划，不运行 Resolve，不自动制作预览。失败可能留下 draft 或已生成文件，重试前先查看，不覆盖。计划路径跨目录移动时重写 project_root，保留素材路径含义；跨盘无法生成相对根时会报错。

## 并发与恢复边界

带 workspace 的命令持有 .codex-resolve.lock，防止协作 CLI 并发推进同一项目。该锁不阻止 Resolve UI 或其他编辑器改文件。进程异常退出可能留下锁；检查 pid 和操作记录，确认没有任务仍在运行后再由用户或 agent 在授权范围清理。

事件记录包含 state_after。若命令完成但状态写入失败，错误会包含实际结果；不能盲目重跑写操作。可以依据历史事件和落盘操作记录人工重建 state.json；本版本没有自动事件重放或 Resolve 回滚。checkpoint 现在包含项目状态、两份交接和创作意图，仍不备份媒体、计划目录或 Resolve 数据库。
