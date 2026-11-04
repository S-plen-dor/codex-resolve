# Codex Resolve

通过与 Codex 自然语言对话，在 DaVinci Resolve 21 中完成视频剪辑、修改与导出。

**开发预览：0.1.0.dev2。当前提供创作闭环和项目续接的首批接口，尚不是完整的一键剪辑产品。此次移植与新增代码未运行测试，也未连接或修改 Resolve 工程。**

## 使用目标

你已安装 Codex 和 DaVinci Resolve Studio 21，将素材交给 Codex：

> 把这些素材剪成 30 秒音乐高光，节奏强一些，保留完整转身动作。
>
> 中间太碎了，减少两次切镜，最后那个表情放大一点。
>
> 导出 4K，并保留可以继续修改的工程。

用户表达创作意图；Codex 维护素材分析、剪辑计划、当前版本及执行记录。项目面向单机位、同步多机位、多场次混剪和音乐短片，按真实案例逐步扩展。

## 创作自由

项目提供剪辑能力与可靠执行机制。风格、镜头密度、是否卡点、动作是否完整、变速方式、声音处理和视觉效果由当前用户与项目决定；没有全局审美模板。案例和预设均为可选参考，不将原作者的偏好应用到其他用户。

用户可指定方案、让 Codex 自主创作，或边预览边探索。工具的技术限制应如实说明，并允许通过其他可用接口或项目专用实现扩展；现成工具清单不构成创作白名单。人物写实或风格化等要求也由当前任务确定。

## 当前具有什么

| 内容 | 开发状态 |
|---|---|
| 媒体规格、精确抽帧、接触表、同步候选、音频特征、技术 QC | 从本地工具库提取；移植后未运行验证 |
| 中文 ASR、给定歌词对齐、候选 SRT | 可选本地模型；移植后未运行验证 |
| Fusion 运镜、持久化、慢放 helper | 显式对象接口；历史有限验证，移植后未运行验证 |
| 项目初始化、状态查看、记录检查点 | 新增实现；未运行验证 |
| Resolve 只读状态查询 | 新增官方脚本模块适配；未运行验证 |
| 素材观察包 | 新增粗/密抽帧、索引及可选连续短片；未运行验证 |
| 剪辑计划、版本差异 | 新增结构检查、素材可选哈希核对及镜头 ID 差异；未运行验证 |
| 独立时间线构建 | 新增原速切镜、多轨音视频、静态构图、备份及操作记录；未运行验证 |
| 预览渲染 | 新增命名预设排队、显式启动与单次状态查询；未运行验证 |
| 项目续接 | 可选 workspace 自动记录历史、状态和交接，resume 检查记录；未运行验证 |
| 反馈修订 | 按时间区间定位 ID、按精确基础计划修订新版本、保护指定镜头；未运行验证 |
| 自然语言剪辑 Skill | 已编写，需在真实会话验证 |
| 自主创作与反馈 | Codex 根据真实观察维护计划；尚无独立自动创意算法或反馈解析器 |
| 复杂计划执行、原地增量修改、自动审片循环 | 尚未实现 |
| Motion / Design 接入 | 可选协作协议；不捆绑第三方 Skill |

当前 Codex 可依据 Skill 编排观察包、计划、有限的时间线执行器与预览任务，并通过实际可用的观看工具迭代。整个链路尚未运行验证，也不自动理解音乐或反馈。操作入口见 [创作闭环](docs/CREATIVE_LOOP.md)，边界见 [能力清单](docs/CAPABILITIES.md)。

跨对话续接与反馈修订见 [项目续接](docs/PROJECT_CONTINUITY.md)。Codex 解释自然语言后调用修订接口；命令本身不理解“太碎”“第二个特写”等语义，也不自动修改 Resolve 时间线。

## 安装与开始

首发开发目标：Windows、Python 3.12、Codex、Resolve Studio 21。普通版及其他系统未验证。

在仓库目录运行以下命令（这是安装说明，本次整理未执行这些命令）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\cr-media.exe doctor
.\.venv\Scripts\codex-resolve.exe resolve-status
```

另外安装 FFmpeg，并将 `ffmpeg` 加入 PATH。Resolve 外部脚本配置见 [安装说明](docs/INSTALL.md)。依赖版本范围是候选范围，尚未生成经验证的锁定环境。

将 `skills/resolve-edit` 复制到本机 Codex 可发现的 Skills 目录，重启或重新加载技能后调用 `$resolve-edit`。可以让 Codex 按当前版本的安装约定完成复制；无需覆盖已有同名技能。

在 Codex 中说：

> 使用 resolve-edit。项目新建在我指定的目录，素材位于……。目标 30 秒竖屏高光。先检查素材，自主制作初稿，然后根据我的反馈修改。不要覆盖原素材和旧版本。

Codex 可使用 `codex-resolve init NEW_DIRECTORY --name "My edit"` 创建项目记录。项目所在目录已有其他文件时，选择新的子目录。详见 [工作流](docs/WORKFLOW.md)。

## 项目结构

```text
skills/resolve-edit/   自然语言剪辑入口和按需参考
src/focus_mv/         提取的媒体、同步、Fusion、歌词和 QC 工具
src/codex_resolve/    新的项目状态与 Resolve 连接支持
examples/            无个人素材的计划与配置示例
docs/                架构、安装、能力、路线和来源
```

代码采用 [MIT License](LICENSE)；第三方软件、模型、Skills 和媒体不随仓库分发。来源见 [SOURCE_PROVENANCE.md](docs/SOURCE_PROVENANCE.md)，第三方边界见 [THIRD_PARTY.md](THIRD_PARTY.md)。
