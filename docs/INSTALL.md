# 安装与配置

本文件是待验证安装路径。本次未安装、测试或修改宿主配置。

## Python 与媒体工具

使用独立 Python 3.12 虚拟环境，安装仓库：`python -m pip install -e .`。不要复用旧项目中的 site-packages，也不要覆盖系统 Python。

FFmpeg 由用户自行安装。默认从 PATH 查找；可设置 `CODEX_RESOLVE_FFMPEG` 指向可执行文件。

可选：将 examples/environment.example.json 复制为当前工作目录的 environment.local.json，填写本机位置。也可通过 CODEX_RESOLVE_CONFIG 显式指定文件。相对配置路径以配置文件目录解析，环境变量优先。

ASR 单独安装 `python -m pip install -e ".[asr]"`，将 CODEX_RESOLVE_ASR_MODEL 设置为已下载的兼容 faster-whisper 模型目录。工具不会自动下载模型；目录需包含 config.json、model.bin、tokenizer.json、vocabulary.txt。

## Resolve 本地连接

1. 打开 DaVinci Resolve Studio 21。
2. Preferences → System → General → External scripting 选择 Local。具体名称以安装版本为准。
3. 使用安装随附的 Developer/Scripting/README.md 确认 Python、脚本模块与动态库配置。
4. 适配器尝试查找标准安装下的 DaVinciResolveScript.py；自定义安装可设置 RESOLVE_SCRIPT_API。动态库不能加载时按官方文档设置 RESOLVE_SCRIPT_LIB。
5. 运行 `codex-resolve resolve-status` 只读查看当前工程与时间线。

连接成功只证明可以读取状态。它不证明导入、动画、保存、渲染或编码器配置全部可用。Resolve 21.1 内置 Python 与文件分析的 Python 3.12 可以分开使用；不要向内置解释器强行注入不兼容的扩展包。

## Codex Skill

使用codex-resolve skill-copy DESTINATION，或将仓库skills/resolve-edit整个文件夹复制到当前Codex支持的Skills位置。用当前官方安装约定确认位置；先检查是否已有同名 Skill，不覆盖用户修改。

Skill 自带工作流参考，但 Python 包需另外安装。用户没有激活虚拟环境时，Codex 应使用虚拟环境中命令的完整路径。此处未自动安装 Skill 或改变任何用户配置。

## 故障定位

- 找不到 FFmpeg：检查 PATH 或 CODEX_RESOLVE_FFMPEG。
- 找不到 Resolve 模块：检查 RESOLVE_SCRIPT_API 与安装随附的脚本目录。
- 返回空连接：确认应用已经完成启动、Studio 版本及 Local 脚本配置。
- 原生扩展无法导入：确认文件工具使用 Python 3.12 独立环境。
- 无模型：仅启用基础工具，或显式配置本地模型。

可使用scripts/bootstrap.ps1安装开发包，并用skill-copy显式复制Skill；wheel配置已包含Skill参考，但打包和安装均未运行验证。跨系统和精确依赖锁定仍待完善。
