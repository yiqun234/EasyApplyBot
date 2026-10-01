# EasyApplyBot 项目说明

## 项目用途

EasyApplyBot 是一个基于 Selenium 的 LinkedIn Easy Apply 自动化项目，同时提供单账号主控制界面和多账号调度界面。

核心入口：

- `start.bat`：Windows 主入口，创建/复用 `venv` 后启动 `gui_web_tkinter.py`。
- `start_scheduler_ui.bat`：Windows 调度入口，创建/复用 `venv` 后启动 `scheduler_gui.py`。
- `main.py --config <yaml>`：单个账号的机器人命令行入口。
- `scheduler.py`：无界面的多账号定时执行入口。
- `linkedineasyapply.py`：LinkedIn 搜索、列表遍历、Easy Apply 表单和上传等核心业务逻辑。
- `application_limits.py`：机器人与调度器共用的每日限额异常和退出码；限额仅结束当前这一轮，允许再次运行。

`gui_tkinter.py` 是旧版 GUI；当前 `start.bat` 不启动它。除非用户明确要求维护旧 GUI，否则主界面修改应落在 `gui_web_tkinter.py`。

## 版本号

当前发布版本为 `5.1`。

两个当前界面的版本号必须保持一致：

- `gui_web_tkinter.py` 中的 `VERSION`
- `scheduler_gui.py` 中的 `VERSION`

发布安装包时必须检查两个值相同，并确保窗口标题在切换语言、登录页和主界面中仍显示版本号。

## 安装包更新触发规则

当用户提到“更新安装包”“更新打包代码”“同步安装包”“重新打包”“覆盖安装包”“生成 ZIP”“发布新版”或含义相同的中英文表达时，必须在完成业务代码修改后继续执行本节流程，不能只修改源码目录。

发布位置：

- 安装包目录：`/Users/lian/Project/foreign/Remote/EasyApplyBot/`
- ZIP 文件：`/Users/lian/Project/foreign/Remote/EasyApplyBot.zip`

源码目录 `/Users/lian/Project/foreign/webs/EasyApplyBot/` 是业务代码的唯一来源。将本次相关业务代码同步到安装包目录，并覆盖同名旧文件。通常需要同步：

- `linkedineasyapply.py`
- `application_limits.py`
- `main.py`
- `gui_web_tkinter.py`
- `scheduler.py`
- `scheduler_gui.py`
- `auth_server.py`
- `firebase_manager.py`
- `requirements.txt`
- `start.bat`
- `start_scheduler_ui.bat`
- `config_demo.yaml`
- `lang/`
- `vendor/cft-versions.json`
- `LICENSE`
- 本文件 `AGENTS.md`

如果相关功能改到了其他运行时文件，也要一并同步。`setup.bat` 目前只存在于安装包目录，除非用户要求修改安装流程，否则保留它。

不得用开发目录的下列文件覆盖或污染安装包：

- `config.yaml`、`configs/`（真实账号配置）
- `auth.json`
- 简历、照片和 Cover Letter
- `applied_jobs*.json`、公司黑名单、CSV 输出
- `chrome_bot/`、`venv/`、缓存、日志、截图和临时文件
- `.git/`、`.kiro/`、`__pycache__/`、`.DS_Store`、`__MACOSX/`

安装包目录中已有的 `config.yaml` 默认保留，不从开发目录覆盖；只有用户明确要求更新默认账号配置时才修改。

## 打包流程

1. 确认本次相关代码已保存，检查两个 GUI 的 `VERSION` 相同。
2. 对 Python 文件执行 `py_compile`，运行与改动相关的测试。
3. 将上面的业务文件同步到 `/Users/lian/Project/foreign/Remote/EasyApplyBot/`。
4. 清理安装包目录中的 `.DS_Store`、`__pycache__` 和 `.pyc`。
5. 在 `/Users/lian/Project/foreign/Remote/` 中生成临时 ZIP，再原子覆盖 `EasyApplyBot.zip`。ZIP 顶层必须是 `EasyApplyBot/`，不能包含 `__MACOSX`。
6. 执行 `unzip -t`，并检查 ZIP 中没有账号配置目录、认证文件、简历、浏览器资料或运行日志。
7. 对安装包目录中的 Python 文件再执行一次 `py_compile`，并核对关键源码与开发目录一致。

两个 GUI 都支持无界面的版本检查，可用于源码和安装包冒烟测试：

```bash
python gui_web_tkinter.py --version
python scheduler_gui.py --version
```

推荐的 ZIP 命令：

```bash
cd /Users/lian/Project/foreign/Remote
zip -r -X EasyApplyBot.zip.tmp EasyApplyBot \
  -x '*/.DS_Store' '*/__pycache__/*' '*.pyc' '*/venv/*' '*/chrome_bot/*'
mv -f EasyApplyBot.zip.tmp EasyApplyBot.zip
unzip -t EasyApplyBot.zip
```

## 修改和验证原则

- 保留旧版 LinkedIn 界面的选择器，同时为新界面增加语义选择器或 Shadow DOM 兼容。
- 在线测试必须使用慢速节奏，不得高频连续点击职位卡片；避免触发 LinkedIn HTTP 429。
- 未经用户明确授权，不要用真实主账号做提交测试。
- 上传测试前必须确认文件存在、格式可接受且路径适合目标操作系统。
- 安装包发布验证只检查程序入口、导入、版本和文件完整性；不要为了验证安装包而额外提交 LinkedIn 申请。
- 不覆盖与当前任务无关的用户修改，也不自动提交 Git commit。
