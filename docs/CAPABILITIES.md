# 能力与证据

2026-11-04：本次按用户要求跳过全部运行测试。新代码与移植代码均为 unverified_port。未启动 Resolve、修改工程或生成成片。

历史工具库 0.2.0 的记录：基础文件工具曾使用合成素材验收；Fusion 缩放经历独立工程、DRP 往返、保存重开和 360×640/59.94 实际渲染；慢放仅对小尺寸合成素材的 80% 与 100→80% 进行有限验证。历史另有二维透明图形的本机 4K 生产案例。这些不构成本仓库运行通过的证明。

| 能力 | 当前实现 | 限制 |
|---|---|---|
| doctor / cache-check | 已移植 | 候选依赖未锁定；完整源码变化会使缓存失效 |
| probe / frames / paired-frames / cover | 已移植 | 配对工具要求同帧率、连续时间戳；旋转与精度仍需实际复核 |
| sync | 已移植 | 音频同步候选；重复音乐、现场延迟、漂移需复核 |
| features | 已移植 | RMS、频带、谱通量；无确认拍点和情绪识别 |
| qc / audio-check | 已移植 | 不是完整感知验收；波形模式是单声道比较 |
| asr / lyrics-align / lyrics-export | 可选移植 | 中文、本地模型、机器候选；不是歌词自动审核 |
| retime-plan / retime-check / cache-match | 已移植 | 当前计划 0<speed<=1；不是任意速度坡道 |
| focus_mv.fusion / retime.apply | 已移植 | 显式 Resolve 对象、未处理合成；不自动建项目 |
| init / project-status / checkpoint | 新增 | 仅项目记录管理，非 Resolve 回滚 |
| resolve-status | 新增 | 只读连接，无应用启动或写入 |
| observe | 新增，未运行验证 | 帧索引抽样、名义时间索引、可选60秒以内短片；不做语义识别 |
| plan-validate / plan-diff | 新增，未运行验证 | 结构、路径、可选哈希与 ID 差异；不是执行或审美验收 |
| plan-apply | 新增，未运行验证 | 同帧率规则视频、多轨、静态构图、camera/opacity/有限慢放、独立音频增益/淡化；新时间线与前后DRP |
| render-submit / render-status | 新增，未运行验证 | 已有预设、显式尺寸/帧率/声音开关、分段或全片、排队/启动与状态查询 |
| --workspace / plan-register / resume | 新增，未运行验证 | 可选作用域、自动事件/状态/交接、只读续接；不恢复 Resolve |
| plan-locate / plan-revise | 新增，未运行验证 | 时间范围查 ID、匹配基础哈希的新计划、保护指定片段；自然语言由 Codex 解释 |
| produce | 新增，未运行验证 | 可选反馈修订→新工作版本→预览排队/启动；异步，不自动观看 |
| render-collect / review-record | 新增，未运行验证 | 实际视频/hash、可选QC/观察包、保存审片声明；声明不是独立感知证明 |
| skill-copy / resolve-capabilities / operation-check | 新增，未运行验证 | 显式目录复制、只读方法/预设发现、live结构/属性对照；不是兼容性或完整图审计 |
| 原地增量修改 / 自动恢复 | 未实现 | 当前新计划与新时间线迭代；审片判断由Codex/用户负责 |
| 自动追踪、人物分割、跨场次匹配 | 未迁入 | 不因历史项目有脚本就声称通用支持 |
| Huashu Motion / Design | 协议与指导 | 用户自选、自行安装；未做本仓库联调 |

源码导入不触发 Resolve 操作。CLI 调用可能写入用户明确指定的新路径。媒体命令退出码沿用 0 成功、1 执行错误、2 检查未通过；项目 CLI 为 0 成功、1 错误。

查函数时按需阅读对应模块或运行 `cr-media --help` / `cr-media COMMAND --help`。本次未执行 help、doctor、安装或集成测试。

新命令的副作用、协议与限制见 [END_TO_END.md](END_TO_END.md)。plan-apply/produce 会保存当前工程、导出前后DRP、生成媒体和Fusion合成、新建工作时间线；渲染提交改变交付设置并排队，只有 --start 才启动。普通版、跨系统、异帧率、VFR、自动抠像、任意OFX、任意速度曲线、自动调色和真人光流画质仍未覆盖或未验证。这些是当前适配器边界，不是创作规则。
