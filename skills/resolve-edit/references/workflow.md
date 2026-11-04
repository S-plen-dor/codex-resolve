# 调用与编排参考

## 工具发现

`codex-resolve --help`：init、project-status、checkpoint、resolve-status。

项目续接：resume DIRECTORY；plan-register PLAN --workspace DIRECTORY。观察、修订、构建和渲染命令支持 --workspace，自动维护 state.json、history/ 与 HANDOFF.auto.md。先读自动交接再读人工 HANDOFF.md 与创作意图；不要以记录代替 live 工程检查。未提供 workspace 时不自动选项目或更新状态。

反馈修改：plan-locate PLAN --start FRAME [--end FRAME] 返回时间线区间中的视频/音频 ID；语义指代仍由你结合预览解释。将用户原话、解释、基础 SHA-256、preserve_ids 和 update/add/remove 操作写成 changes，再用 plan-revise PLAN --changes FILE --out NEW_PLAN --revision NEW_REVISION --workspace DIRECTORY。set 对字段整体替换，不自动 ripple。之后比较计划，再构建新工作版本。详见仓库 docs/PROJECT_CONTINUITY.md。

创作入口还包括produce、render-collect、review-record、resolve-capabilities、operation-check和skill-copy；完整计划约定按需读plan-contract.md。具体参数先看子命令 help；仓库 docs/CREATIVE_LOOP.md 包含协议及副作用说明。observe 生成真实图像/索引及可选短片，必须通过当前会话观看工具实际打开后才能描述观察结论。无法看视频或听音时明确边界。

plan-apply 要求 --project、唯一 --timeline、新 --out 和 --save-current；会保存当前工程并导出DRP备份，再构建同帧率多轨时间线。已接入camera/opacity/有限慢放及独立音频增益/淡化；未支持的效果改用其他适配器，不静默降级。render-submit 从 operation.json 定位目标，--preset 指向已有预设，默认排队，--start 显式启动。render-status 只查一次任务状态；队列完成后用render-collect关联实际视频，可选按任务范围做QC/观察，再通过review-record保存真实范围内的审片声明。不要把分段预览认可成整片通过。

`cr-media --help`：doctor、cache-check、probe、frames、paired-frames、cover、sync、features、qc、audio-check、asr、lyrics-align、lyrics-export、retime-plan、retime-check、cache-match。需要时读取子命令 help，使用明确的新输出路径。ASR 可选，模型仅本地读取。

Fusion helper 位于 focus_mv.fusion；慢放应用位于 focus_mv.retime。它们需显式传入已核对的 Resolve 对象，不自动连接、选工程或渲染。仅对未处理合成使用，复杂已有链先检查并采用独立副本。

## 阶段

以下是可组合的工作步骤，不是必须逐项执行的创作流程。按用户任务跳过无关分析、提案或设计模块；不额外强制三方向、固定时长、音乐卡点或某种视觉风格。当前项目中的推断与偏好不自动成为跨项目默认值。

1. 需求与环境：目标时长、音乐/主音源、素材、画幅、输入色彩、交付范围；能从任务推断的不用重复问。
2. 素材：先读有效缓存。粗抽帧发现候选，再加密和连续短段检查动作。同步候选用多点动作与口型复核。
3. 计划：按镜头保存稳定 id、素材 id、源/时间线范围、剪辑理由、构图与效果。没有确认拍点时保留候选标签。
4. 执行：核对目标、保存可恢复版本、创建工作时间线。符合有限执行器范围时使用 plan-apply；复杂需求通过当前实际可用的 Resolve 工具或官方脚本完成。
5. 预览：先处理代表性难点，再扩展。记录 API 真实返回、实际片段时长、帧绑定及渲染任务状态。
6. 修改：将用户反馈定位到镜头 id 和区间，保留已认可部分，另存计划和工作版本。用 plan-diff 对比；当前通过新时间线全量构建下一版，不声称原地局部执行。保存创作判断及用户反馈，避免没有新依据的无限自改。
7. 交付：按要求检查规格、音频、构图和连续段，明确未检查项，更新 HANDOFF.md。

## 交接约定

project.json 保存项目事实；state.json 保存当前进展；plans/ 保存计划版本。路径相对项目目录，素材身份与内容指纹另存分析记录。状态由 agent 维护；当前工具只创建与查看记录、保存记录检查点。

每次完成一次修改，HANDOFF.md 写入用户原话、已接受决定、检查范围和未解决问题；--workspace 自动交接保存计划、操作/渲染指针与工具建议的下一步。新聊天用 resume 读取上下文，不重新扫描全部素材。render_complete_not_reviewed 不等于用户认可，计划一旦变化旧预览不再代表当前版本。

## 已知易错点

这些提醒用于发现非预期问题。用户有意使用的跳切、黑帧、重复、失真、不同步或特殊声道处理应按创作意图记录，不能因偏离普通连续剪辑就判为失败。确定性技术检查与审美评价分别报告。

- 60 与 60000/1001 不相等；图形顺应不能顺带改变实拍主音。
- 静态属性不代表动画；保存返回成功不代表重开后动画还在。
- 光流需要检查头发、手指、交叉肢体，不能仅凭速度值保证质量。
- 音频相关性可能漏掉重复混音、增益错误和单声道下混。
- 接口参数被拒绝时不能用目标文件名冒充已经设置成功。
- 公开的效果参考与项目专用脚本不等于已经验证的公共工具。
