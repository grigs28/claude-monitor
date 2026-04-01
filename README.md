# 智能确认器 / Smart Confirmer

自动监控 [Claude Code](https://claude.ai/code) 会话，实时响应权限确认提示。

Auto-monitors [Claude Code](https://claude.ai/code) sessions and responds to permission confirmation prompts in real time.

支持两种模式：
- **Tmux 模式** (`--tmux`) — 轮询 tmux 屏幕内容，自动点击确认按钮
- **Hook 模式** (`--hook`) — 集成 Claude Code `PermissionRequest` hook，实时 allow/deny

Supports two modes:
- **Tmux Mode** (`--tmux`) — Polls tmux pane content and auto-confirms prompts
- **Hook Mode** (`--hook`) — Integrates with Claude Code `PermissionRequest` hook for real-time allow/deny

判断策略：**规则优先 → AI 兜底**。规则匹配常见场景零延迟，未命中的交给本地 Qwen 模型判断。

Decision strategy: **Rules first → AI fallback**. Rule-matched common scenarios respond instantly; unmatched requests are forwarded to a local Qwen model.

> **建议使用本地部署的 AI 模型**（如 Qwen、LLaMA 等），避免调用云端 API 产生不必要的费用。
> **Using a locally deployed AI model** (e.g., Qwen, LLaMA) is recommended to avoid unnecessary cloud API costs.

## 功能特点 / Features

- 规则优先，AI 兜底（`--ai` 开启）
- Rule-first decision-making with AI fallback (`--ai` flag)
- Hook 模式支持 `--allow-all` 全部允许
- Hook mode supports `--allow-all` to permit all requests
- 内置危险命令拦截（`rm -rf /`、`dd`、`mkfs`、`fork 炸弹` 等）
- Built-in dangerous command blocking (`rm -rf /`, `dd`, `mkfs`, fork bombs, etc.)
- 内置安全命令白名单（`git status`、`ls`、`pytest`、`Read`/`Glob`/`Grep` 等）
- Built-in safe command whitelist (`git status`, `ls`, `pytest`, `Read`/`Glob`/`Grep`, etc.)
- 纯规则模式零依赖（仅需 tmux）；AI 模式额外需要 `requests`
- Zero-dependency rule-only mode (tmux only); AI mode additionally requires `requests`
- `.env` 文件配置，支持自定义允许/拒绝规则
- `.env` configuration with custom allow/deny rules support
- 单文件应用，开箱即用
- Single-file application, ready to run

## 快速开始 / Quick Start

### 前置条件 / Prerequisites

- Python 3.8+
- tmux（Tmux 模式必需 / Tmux Mode required）
- 可选：本地 LLM API（如 Qwen），用于 AI 兜底 / Optional: Local LLM API (e.g., Qwen) for AI fallback

```bash
# 安装依赖（可选，仅 --ai 模式需要）
pip install requests python-dotenv

# Install dependencies (optional, only needed for --ai mode)
```

### 命令行参数 / CLI Arguments

```
python smart_confirmer.py --tmux [会话名] [--ai]
python smart_confirmer.py --hook [--ai] [--allow-all]
```

| 参数 / Argument | 说明 / Description |
|------------------|---------------------|
| `session` | tmux 会话名（默认 `claude`） / tmux session name (default: `claude`) |
| `--tmux` | Tmux 轮询模式：监控屏幕并自动确认提示 / Tmux polling mode: monitors screen and auto-confirms prompts |
| `--hook` | Hook 模式：PermissionRequest 事件处理 / Hook mode: PermissionRequest event handling |
| `--ai` | 启用 AI 兜底（规则不匹配时调用本地模型） / Enable AI fallback when rules don't match |
| `--allow-all` | Hook 模式下全部允许（跳过所有规则检查） / Allow all in hook mode (skip all rule checks) |

### Tmux 模式 / Tmux Mode

监控 tmux 会话，自动确认 Claude Code 的权限提示。

Monitors tmux sessions and auto-confirms Claude Code permission prompts.

```bash
# 纯规则模式（无需 AI）
python smart_confirmer.py --tmux claude

# Rule-only mode (no AI needed)
python smart_confirmer.py --tmux claude

# AI 兜底模式（规则优先，未命中时调用本地模型）
python smart_confirmer.py --tmux claude --ai

# AI fallback mode (rules first, local model for unmatched)
python smart_confirmer.py --tmux claude --ai

# 指定 tmux 会话名
python smart_confirmer.py --tmux my_session --ai

# Specify tmux session name
python smart_confirmer.py --tmux my_session --ai
```

工作流程 / Workflow:

```
轮询 tmux 屏幕 → 关键词检测 → 规则匹配 → AI 兜底 → 发送按键
Poll tmux screen → keyword detection → rule match → AI fallback → send keys
```

- 检测到 `requires approval`、`do you want`、`proceed` 等关键词时触发
- Triggers on keywords like `requires approval`, `do you want`, `proceed`
- 优先选 "always allow"（选项 2），否则选 "Yes"（选项 1）
- Prefers "always allow" (option 2), otherwise selects "Yes" (option 1)
- 冷却期内不重复确认，防止误触
- No repeat confirmations during cooldown to prevent accidental triggers

### Hook 模式 / Hook Mode

集成 Claude Code 的 `PermissionRequest` hook，逐条判断工具调用是否允许。

Integrates with Claude Code `PermissionRequest` hook to allow/deny tool calls one by one.

**基础用法** — 规则判断 allow/deny / **Basic usage** — rule-based allow/deny:

在 Claude Code 的 `settings.json` 中配置 / Configure in Claude Code `settings.json`:

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/smart_confirmer.py --hook"
          }
        ]
      }
    ]
  }
}
```

**全部允许** — 跳过所有检查，直接 allow（适合可信环境）/ **Allow all** — skip all checks, direct allow (for trusted environments):

```json
"command": "python3 /path/to/smart_confirmer.py --hook --allow-all"
```

**AI 兜底** — 规则不匹配时交给本地模型判断 / **AI fallback** — local model for unmatched rules:

```json
"command": "python3 /path/to/smart_confirmer.py --hook --ai"
```

**手动测试 / Manual testing:**

```bash
# 测试允许规则（git status 应该被允许）
echo '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | python3 smart_confirmer.py --hook

# Test allow rules (git status should be allowed)

# 测试拒绝规则（rm -rf 应该被拒绝）
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | python3 smart_confirmer.py --hook

# Test deny rules (rm -rf should be denied)

# 测试全部允许
echo '{"tool_name":"Bash","tool_input":{"command":"anything"}}' | python3 smart_confirmer.py --hook --allow-all

# Test allow all
```

工作流程 / Workflow:

```
stdin JSON → 全部允许? → 拒绝规则 → 允许规则 → AI 兜底 → stdout JSON
stdin JSON → allow all? → deny rules → allow rules → AI fallback → stdout JSON
```

**判断优先级 / Decision priority:**

1. `--allow-all` — 直接允许所有请求 / Directly allow all requests
2. 拒绝规则 — 匹配危险命令则 deny / Deny rules — deny on dangerous command match
3. 允许规则 — 匹配安全命令则 allow / Allow rules — allow on safe command match
4. AI 兜底 — 本地模型判断（需 `--ai`） / AI fallback — local model judgment (requires `--ai`)
5. 无匹配 — 走默认流程 / No match — default behavior

**内置拒绝规则（即使 `--allow-all` 之外也会拦截）/ Built-in deny rules (always intercept, even with `--allow-all`):**

| 模式 / Pattern | 匹配命令 / Matches |
|----------------|--------------------|
| `rm\s+-rf\s+/` | `rm -rf /` |
| `:\(\)\{.*:\|:&\}` | Fork 炸弹 / Fork bomb |
| `dd\s+if=.*of=/dev/` | `dd` 写设备 / `dd` writing to device |
| `curl\|wget ... \| sh` | 管道执行远程脚本 / Pipe remote script execution |
| `mkfs` | 格式化磁盘 / Format disk |
| `iptables` | 防火墙规则 / Firewall rules |
| `chmod\s+-R\s+777\s+/` | 全局写权限 / Global write permissions |
| `shutdown\|reboot` | 关机重启 / Shutdown/reboot |

另外，`Write`/`Edit` 写入 `/etc/`、`/boot/`、`/sys/`、`/proc/` 路径也会被拦截。
Additionally, `Write`/`Edit` writing to `/etc/`, `/boot/`, `/sys/`, `/proc/` is also blocked.

**内置允许规则 / Built-in allow rules:**

| 类别 / Category | 规则 / Rules |
|-----------------|--------------|
| 安全工具 / Safe tools | `Read`、`Glob`、`Grep`、`WebSearch`、`WebFetch`、`mcp__*` |
| Git 只读 / Git read-only | `git status`、`git log`、`git diff`、`git branch`、`git show` 等 / etc. |
| 系统查看 / System view | `ls`、`cat`、`head`、`tail`、`pwd`、`whoami`、`which`、`echo`、`find` |
| 构建/测试 / Build/test | `npm test/run/lint/install`、`pytest`、`make` |

### 停止运行 / Stopping

```bash
# 发送信号停止 / Send signal to stop
kill <PID>

# 或创建停止文件 / Or create stop file
touch .stop
```

## 配置 / Configuration

复制 `.env.example` 到 `.env` 并按需修改 / Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### AI 模型配置（`--ai` 模式生效）/ AI Model Configuration (effective in `--ai` mode)

| 变量 / Variable | 默认值 / Default | 说明 / Description |
|-----------------|------------------|---------------------|
| `QWEN_API_URL` | `http://192.168.0.70:5564/v1/chat/completions` | 本地 AI API 地址 / Local AI API address |
| `QWEN_MODEL` | `/opt/models/Qwen/Qwen3.5-27B-FP8` | 模型名称或路径 / Model name or path |
| `QWEN_TIMEOUT` | `30` | API 请求超时（秒） / API request timeout (seconds) |

### 通用配置 / General Configuration

| 变量 / Variable | 默认值 / Default | 说明 / Description |
|-----------------|------------------|---------------------|
| `COOLDOWN` | `2` | 确认后冷却秒数，防止重复触发 / Cooldown seconds after confirm, prevents re-trigger |
| `RULE_CONTEXT_SIZE` | `1000` | 规则模式截取屏幕字符数 / Screen characters captured in rule mode |
| `AI_CONTEXT_SIZE` | `300` (Tmux) / `1000` (Hook) | 发送给 AI 的字符数 / Characters sent to AI |
| `HEARTBEAT_INTERVAL` | `60` | 无事件时心跳输出间隔（秒） / Heartbeat interval when no events (seconds) |

### Hook 模式配置（`--hook` 模式生效）/ Hook Mode Configuration (effective in `--hook` mode)

| 变量 / Variable | 默认值 / Default | 说明 / Description |
|-----------------|------------------|---------------------|
| `HOOK_ALLOW_PATTERNS` | （空 / empty） | 额外允许的命令模式，逗号分隔正则 / Extra allowed command patterns, comma-separated regex |
| `HOOK_DENY_PATTERNS` | （空 / empty） | 额外拒绝的命令模式，逗号分隔正则 / Extra denied command patterns, comma-separated regex |
| `HOOK_LOG_FILE` | `hook.log` | 日志文件路径 / Log file path |

自定义规则示例 / Custom rules example:

```ini
# 允许 docker compose 相关命令
# Allow docker compose commands
HOOK_ALLOW_PATTERNS=docker\s+compose\s+up,docker\s+compose\s+down

# 拒绝生产环境部署
# Deny production deployments
HOOK_DENY_PATTERNS=deploy\s+--prod,kubectl\s+apply
```

## 架构 / Architecture

单文件应用 `smart_confirmer.py`，两个核心类 / Single-file application `smart_confirmer.py` with two core classes:

- **`FixConfirmer`** — Tmux 轮询模式，持续监控屏幕并自动确认 / Tmux polling mode, continuously monitors screen and auto-confirms
- **`HookHandler`** — Hook 模式，接收 stdin JSON 做实时 allow/deny 决策 / Hook mode, receives stdin JSON for real-time allow/deny decisions

## 模型调度配置 / Model Schedule Configuration

`.model_schedules.json` 用于按时间段自动切换不同的 AI 模型供应商。**此文件包含 API Token，已在 `.gitignore` 中排除，请勿提交到仓库。**

`.model_schedules.json` auto-switches AI model providers by time period. **This file contains API tokens and is excluded in `.gitignore` — do not commit it.**

复制示例文件并填入真实配置 / Copy the example file and fill in real config:

```bash
cp .model_schedules.json.example .model_schedules.json
```

配置说明 / Configuration reference:

| 字段 / Field | 说明 / Description |
|--------------|---------------------|
| `settings_path` | Claude Code 的 `settings.json` 路径 / Path to Claude Code `settings.json` |
| `check_interval` | 检查调度间隔（秒） / Schedule check interval (seconds) |
| `default` | 默认时段的 API 配置（不在任何调度时段内时使用）/ Default API config (used when no schedule matches) |
| `schedules` | 调度列表，按时段切换不同供应商 / Schedule list, switches providers by time period |
| `schedules[].name` | 调度名称（仅用于日志）/ Schedule name (for logging only) |
| `schedules[].start` | 开始时间（HH:MM，24 小时制）/ Start time (HH:MM, 24-hour) |
| `schedules[].end` | 结束时间（HH:MM，24 小时制）/ End time (HH:MM, 24-hour) |
| `schedules[].env` | 该时段使用的 API 配置 / API config for this time period |

`default` 和 `schedules[].env` 中的环境变量 / Environment variables in `default` and `schedules[].env`:

| 变量 / Variable | 说明 / Description |
|-----------------|---------------------|
| `ANTHROPIC_BASE_URL` | API 基础地址 / API base URL |
| `ANTHROPIC_AUTH_TOKEN` | API 认证 Token / API auth token |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Haiku 模型名称 / Haiku model name |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Sonnet 模型名称 / Sonnet model name |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Opus 模型名称 / Opus model name |

## 许可 / License

MIT
