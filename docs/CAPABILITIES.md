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
| 通用 plan apply / incremental edit / render | 未实现 | 后续核心工作 |
| 自动追踪、人物分割、跨场次匹配 | 未迁入 | 不因历史项目有脚本就声称通用支持 |
| Huashu Motion / Design | 协议与指导 | 用户自选、自行安装；未做本仓库联调 |

源码导入不触发 Resolve 操作。CLI 调用可能写入用户明确指定的新路径。媒体命令退出码沿用 0 成功、1 执行错误、2 检查未通过；项目 CLI 为 0 成功、1 错误。

查函数时按需阅读对应模块或运行 `cr-media --help` / `cr-media COMMAND --help`。本次未执行 help、doctor、安装或集成测试。
