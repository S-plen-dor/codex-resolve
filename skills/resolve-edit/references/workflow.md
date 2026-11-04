# 按需调用参考

这是一份工具地图，不是剪辑流程。只查当前需要的部分；直接使用其他接口或项目专用脚本也可以。

| 需要什么 | 可选入口 |
|---|---|
| 查看连接与接口 | resolve-status、resolve-capabilities、operation-check |
| 观察素材 | observe；cr-media probe/frames/cover/features |
| 比较机位与同步 | cr-media sync/paired-frames |
| 使用声明式计划 | plan-validate、plan-register、plan-diff；格式见plan-contract.md |
| 找到片段或修订计划 | plan-locate、plan-revise |
| 构建新工作版本 | plan-apply，或produce串接构建与预览提交 |
| 预览与产物 | render-submit、render-status、render-collect |
| 保存审片意见 | review-record，仅记录真实范围内的声明 |
| 项目交接 | init、project-status、checkpoint、resume、可选--workspace |
| 歌词与慢放辅助 | cr-media asr/lyrics-align/lyrics-export/retime-plan/retime-check/cache-match |

参数需要时查看相应子命令help。命令本身不会自动理解审美或自然语言；由Codex按当前用户意图决定如何使用。

## 选用本包时的非显然约定

- plan-apply/produce会保存当前工程、导出DRP并创建新工作时间线；--save-current表达这项副作用。新输出目录和新时间线名用于保护旧版本。其他实现可采用自己的恢复方式。
- produce只串接到渲染排队或启动；render-status查一次任务。需要完成交付时继续跟进任务与实际产物，不能把排队说成完成。
- --workspace是可选的状态管理。它生成state.json、history/和HANDOFF.auto.md，不覆盖人工HANDOFF.md；不用它不影响通过其他方式剪辑。
- 修改计划后，旧预览不再代表新版本。分段预览文件0帧对应记录的timeline_range起点。
- Fusion helper只接受新建/未处理合成，是这个helper的接口条件；复杂合成可使用其他实现。
- 音频相关、技术解码和图像抽样的证据范围不同；说明实际做了什么即可，不为每个任务增加统一验收清单。

需要恢复已有项目上下文时，可先用resume定位当前产物，也可直接读取已有交接。自动记录不代表live工程已核对。人物表现、动作完整性、声音是否连续、是否卡点等均由当前项目决定。
