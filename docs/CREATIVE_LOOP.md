# 素材观察、创作与预览迭代

本轮新增代码均未运行测试。下面是可调用接口的设计与实现说明，不代表已成功制作视频。无固定风格、片长或节奏要求；创作选择归当前用户。命令由 Codex 维护和执行，用户不必手写计划。

## 1. 看真实素材

```powershell
codex-resolve observe media/source.mp4 --out analysis/overview --interval 5
codex-resolve observe media/source.mp4 --out analysis/candidate-01 --start 300 --end 600 --interval 0.25 --width 720 --clip
```

start/end 是零起点源帧，[start,end)。默认范围依赖容器报告的帧数；没有帧数时显式给 --end。每包不超过500张，连续短片最长60秒，拆分范围后逐步观察。输出 observation.json、INDEX.md、精确帧图与接触表；--clip 生成带原音的720宽预览。

图片是按帧索引提取；秒数来自名义帧率，短片按时间 seek，不构成 VFR 精确映射。长素材先用粗采样发现候选，再加密。生成包不等于 Codex 已看过，必须使用当前会话可用的图像/视频/音频工具打开实际产物。不能观看连续视频或听音时明确边界，不编造看过/听过的结论。

## 2. 设计镜头

在 creative-brief.md 记录情绪、参考为何相关、当前创作判断及用户已接受决定。不要求固定提案，不以检测分数代替选镜。

以 examples/edit-plan.example.json 为起点创建 plans/v001.json。project_root 相对计划文件目录解析，素材路径再相对项目根解析。推荐将素材 SHA-256 从观察记录填入来源，防止文件变化；缺失时结构检查不提供内容身份保证。

计划中镜头和音频各有稳定 id；source_range/timeline_range 为帧区间，track 为从1开始的轨道索引。audio 是独立片段数组，可连续、切分、多轨叠加或为空。输入源 fps 使用有理数字符串；首个执行器要求源与时间线同帧率、正常速度、规则时间戳及带视频的媒体文件。

```powershell
codex-resolve plan-validate plans/v001.json
codex-resolve plan-diff plans/v001.json plans/v002.json
```

结构检查验证文件存在、可选哈希、ID、范围及同轨重叠；不解码素材、不审批审美。相同轨道的重叠需要后续显式转场适配器，目前可将叠放素材安排在不同轨道。

## 3. 构建独立版本

```powershell
codex-resolve plan-apply plans/v001.json --project MY_PROJECT --timeline WORK_V001 --out versions/build-v001 --save-current
```

这是写入命令。用户已经授权剪辑后，Codex 结合当前工程确定目标。--save-current 明确允许保存当前工程；执行器随后导出 before.drp，创建新工作时间线，不切换其他工程、不覆盖现有同名时间线。工程中其他未保存修改会随当前工程保存，执行前应检查用户工作上下文。

当前实现支持：原速切镜、多视频轨、显式 mono/stereo 音轨，和静态 ZoomX/ZoomY/Pan/Tilt/RotationAngle/Opacity。properties 的单位沿用安装版本的 Resolve API，使用前查接口定义。效果、变速、增益、转场、异帧率或独立音频文件需其他适配器；不静默忽略已请求能力。

操作输出 plan.json、before.drp 与 operation.json。保存每个实际镜头的 id、位置和时长，核对源绑定与源起点。完成状态是 built_not_reviewed。失败为 failed_partial，保留工作时间线与证据，不自动回滚、不继续插入。重复输出目录或时间线名会拒绝执行；这只是重复执行保护，不是自动断点恢复。

构建后尝试恢复之前选中的时间线。工程保存、导出与 readback 不等于重开或渲染验收。调色管理沿用目标工程，不能由本执行器推断输入色彩。

## 4. 提交与观察预览

```powershell
codex-resolve render-submit versions/build-v001/operation.json --out renders/preview-v001 --preset PREVIEW_PRESET --start
codex-resolve render-status renders/preview-v001/render.json
```

必须选择本机已有的命名预设。默认仅排队，--start 仅启动新任务。输出目录必须新建，采用单文件模式和明确范围；预设决定编码、声音和输出画幅等设置，不承诺它符合计划规格。接口拒绝参数时停止并记录，保留已排队任务。

提交前核对工程/时间线 UID 和基本时间线指纹；指纹不是完整 Fusion、调色和属性审计。渲染会改变当前交付设置。开始异步渲染后保留工作时间线，避免渲染中切换；未开始渲染时尝试恢复先前时间线。状态查询不阻塞、不自动检查成片，也不自动恢复时间线。

确认任务完成后定位实际文件，按当前用户约定用 cr-media qc / audio-check / observe 或观看工具检查。渲染完成不是审片通过。把实际结果记录为 reviews/v001.json，可采用 examples/review.example.json；其中观察范围必须真实。

## 5. 修改

将反馈关联 clip id 与区间，在新计划中改动，使用 plan-diff 查看范围。当前方式是新建 WORK_V002 并全量构建新版本，原工作版本保留；尚无原地局部修改器或自动恢复 DRP 命令。

审片同时比较创作意图与实际结果：可以刻意留长镜头，也可以碎切、跳切、黑帧和失真。技术检查提示与创作判断分别记录。用户要求跳过检查时保存 skipped。没有人工反馈时，只根据实际可观察的问题迭代，不能声称模型已完整连续审片。

更新 state.json 和 HANDOFF.md 中当前计划、operation/render 记录、反馈、未决问题及下一步。本轮命令不会自动更新这些 agent 维护的状态，也不自动解析反馈或生成创意计划。
