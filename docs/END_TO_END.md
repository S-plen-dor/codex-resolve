# 从自然语言到可编辑视频：当前完整开发路径

版本 0.1.0.dev3。这里的“完整”指首版核心接口链路已编写：观察、计划、构建、预览、收集、反馈和版本交接。按用户要求未安装运行、未做测试、未连接 Resolve；不承诺稳定可用或任意剪辑需求全部自动化。

## 用户怎样使用

用户在 Codex 中提供素材位置、音乐及创作意图，例如“把这首完整舞台剪得有层次，具体镜头由你设计”。Codex 调用 resolve-edit Skill，检查环境与当前任务，在项目目录维护记录。用户不需要写 JSON，不需要逐镜头确认；关键指代无法确定或缺失事实确实影响结果时才询问。

Codex 使用真实画面作判断，并可按当前会话工具能力观察视频/听音。仅有接触表时明确观察限制，不能声称完成连续审片。首版没有自动选镜模型或独立自然语言解析器；Codex 本身承担理解、审美和镜头设计。

## 安装

已有 Codex、Resolve Studio 21、Python 3.12 和 FFmpeg。在源仓库运行 `scripts/bootstrap.ps1` 建立独立虚拟环境并安装本包；可选 --WithAsr 安装识别依赖、--SkillDestination 指定一个新的 Skill 目录。也可用 pip 安装并调用 `codex-resolve skill-copy DESTINATION`。不覆盖已有 Skill，不自动下载模型，不安装 Resolve 或 FFmpeg。本次未执行安装脚本。

`resolve-status` 查看当前项目；`resolve-capabilities` 查看版本、方法存在性和渲染预设。方法存在不代表接受所有参数，不替代实际兼容性验证。连接配置见 INSTALL.md。

## 一、观察和计划

使用 init 建立新项目、observe 粗看全片，对候选区间加密抽帧/生成短片。将用户意图、参考及暂定创作选择写进 creative-brief.md。对完整舞台可按乐句或自选章节组织观察，时间线长度没有固定30秒限制；长片会增加实际分析、渲染和上下文成本。

计划继续使用 schema_version=1。每个视频/音频片段有稳定 id、源区间与输出时间线区间。用 plan-register 选择计划、plan-validate 检查结构。素材 fps 为有理数；纯音频 source 指定 kind=audio，省略 fps 时按输出时间线帧率解释其区间。所有工具参数的区间仍为零起点 [start,end)。

示例 examples/performance-plan.example.json 展示可组合功能，不是推荐风格或固定参数：

- 多机位可通过不同 source_id 和明确同步区间剪切；同步候选来自已有 cr-media sync/paired-frames。
- 多视频轨和透明素材可叠放；输入色彩、Alpha 和机位匹配由当前任务明确，不自动猜测或重套 LUT。
- properties 使用 Resolve 静态构图参数。
- effects 中 camera 使用局部帧关键点控制 zoom/center_x/center_y/angle。Center 为 Fusion 坐标；不是原像素裁切中心。
- opacity 使用局部帧 keys，范围0..1；可在不同轨上显式交叠片段形成淡化。没有自动生成转场或统一切镜节奏。
- retime 复用原生 SpeedWarp/OpticalFlow helper，支持0<speed<=1恒速慢放或从原速渐慢。source_range 需提供与输出同长度的源句柄，实际消耗由曲线决定。它不是任意速度坡道；快放、倒放等需其他适配器，不能因此禁止用户的创作想法。
- 音频独立列在 audio 中，支持独立 WAV/音乐文件、gain_db、fade_in_frames、fade_out_frames 和mono/stereo。生成新48k/24-bit PCM资产，不修改源文件；切镜和慢放不会自动移动它。声音可以连续、切分、重叠或为空，由计划决定。

所有视频仍要求与时间线同帧率、规则时间戳；异帧率、VFR、复杂抠像、自动跟踪、任意OFX和自动调色不在本执行器范围内。每个效果都保留源工程可编辑性，复用不等于画质已通过。

## 二、一次构建与提交预览

```powershell
codex-resolve produce plans/v001.json --project MY_PROJECT --timeline WORK_V001 --out versions/run-v001 --preset PREVIEW_PRESET --save-current --start --workspace .
```

produce 先检查计划，然后保存当前工程、导出before.drp、新建工作时间线、生成音频/原生Fusion合成、保存并导出editable.drp，最后提交命名预设渲染任务。保留 workflow.json、build/operation.json 和 preview/render.json。默认不启动渲染，--start 才启动；返回后 Codex 需继续查状态，不将排队当完成。

预览可加 `--start-frame 180 --end-frame 360 --width 1080 --height 1920`，只渲染该输出时间线区间。未指定尺寸时显式使用计划尺寸，帧率也来自计划；编码器和质量来自预设。声音开关按audio是否为空确定。接口拒绝设置就停止并记录，不假装已成功。

计划中效果先做逐段，再按效果数组顺序接图；组合在新建的合成中，导出/导回.comp。Fusion动画、中心和透明度在不同版本及真人素材下仍待实际验证。原素材和旧工作时间线保留，自动操作不会关闭重开用户工程。

失败保留 partial 记录、生成资产和新工作时间线。不能盲目重跑；新目录/新时间线保护不等于自动断点恢复。备份DRP不包含所有外部媒体，交付时需保留生成WAV、comp和图形素材路径。可用 operation-check OPERATION 只读对照实际工程结构/属性；不审计整个调色或Fusion内部图。

## 三、找到实际产物

```powershell
codex-resolve render-status versions/run-v001/preview/render.json --workspace .
codex-resolve render-collect versions/run-v001/preview/render.json --out reviews/collection-v001 --workspace .
```

collect 先查询任务是否完成，再识别输出目录中的唯一视频；有多份时显式 --file。写入实际路径、内容哈希、媒体规格、原计划和渲染区间。默认不做全解码与观察。用户允许检查时可加 --qc 生成技术报告，或 --observe 生成接触表；本次没有运行这些检查。分段预览的文件0帧对应记录中 timeline_range 的起点。

技术QC按实际目标帧数、尺寸、帧率检查。黑场仍为候选，不因用户有意黑帧而失败。声音策略及人物瑕疵需按任务另外核验。输出尺寸与原片相同也不等于画质通过。

## 四、观看、反馈与下一版

Codex 或用户观看后，由 Codex 把实际观察范围/用户意见写成声明（examples/review-declaration.example.json），用 review-record COLLECTION --input DECLARATION --out NEW_RECORD --workspace . 保存。status 可 accepted、changes_requested 或 skipped，必须如实写 scope。命令只保存声明，不验证声称的感知过程；接受一段预览不意味着整片通过。

使用 plan-locate 辅助定位反馈对象；Codex 根据预览、镜头理由和对话解释“第二个特写”“副歌太碎”等，再生成changes。可一次完成修订、构建和提交下一版：

```powershell
codex-resolve produce plans/v001.json --changes feedback/change-001.json --revision v002 --project MY_PROJECT --timeline WORK_V002 --out versions/run-v002 --preset PREVIEW_PRESET --save-current --start --workspace .
```

变更仍需匹配基础计划SHA，可保护已认可ID，不自动ripple。暂不支持原地增量修改；每版是新时间线，保持其他镜头决定与参数不变。审片迭代由当前用户目标与实际证据驱动，不强制统一评分，不无限自改。

## 五、续接与交付

--workspace 自动保存历史事件、当前计划、操作/渲染/实际视频/审片声明与自动交接。resume 读取记录并检查缺失/计划外部变化；新聊天仍需核对live工程。自动交接不覆盖人工HANDOFF.md和创作意图。

交付实际视频、editable.drp、生成媒体和设计源文件位置，明确检查范围与未解决问题。导出DRP、技术检查、用户认可分别记录。首版没有自动恢复DRP、自动重放事件、任意效果支持或跨机器稳定性承诺；这些不会被标作已完成。
