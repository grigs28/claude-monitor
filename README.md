# 智能确认器 / Smart Confirmer

自动监控 [Claude Code](https://claude.ai/code) 会话，实时响应权限确认提示。

Auto-monitors [Claude Code](https://claude.ai/code) sessions and responds to permission confirmation prompts in real time.

支持四种模式：
- **Tmux 模式** (`--tmux`) — 轮询 tmux 屏幕内容，自动按 Enter 确认
- **Hook 模式** (`--hook` / `--full`) — 集成 Claude Code `PermissionRequest` hook，实时 allow/deny
- **模型切换** (`--model-switch`) — 按时间段切换 AI 模型供应商（独立进程循环 / hook 单次检查）
- **故障转移** (`--fallback`) — API 连续失败后自动切换到备用模型，可附带模型时间表检查

判断策略：**规则优先 → AI 兜底**。规则匹配常见场景零延迟，未命中的交给本地 Qwen 模型判断。

> **建议使用本地部署的 AI 模型**（如 Qwen、LLaMA 等），避免调用云端 API 产生不必要的费用。

## 功能特点 / Features

- 规则优先，AI 兜底（`--ai` 开启）
- Hook 模式支持 `--allow-all` 全部允许
- 内置危险命令拦截（`rm -rf /`、`dd`、`mkfs`、`fork 炸弹` 等）
- 内置安全命令白名单（`git status`、`ls`、`pytest`、`Read`/`Glob`/`Grep`、`mcp__*` 等）
- 按时间段自动切换模型供应商（`--model-switch`）
- API 连续失败后自动切换备用模型（`--fallback`）
- 一键配置 `--setup` 自动写入 settings.json
- 纯规则模式零依赖（仅需 tmux）；AI 模式额外需要 `requests`
- `.env` 文件配置，支持自定义允许/拒绝规则
- 单文件应用，开箱即用

## 快速开始 / Quick Start

### 前置条件 / Prerequisites

- Python 3.8+
- tmux（Tmux 模式必需）
- 可选：本地 LLM API（如 Qwen），用于 AI 兜底

```bash
pip install requests python-dotenv
```

### 一键配置 / One-Step Setup

```bash
# 一键配置（推荐）
# 安装 PermissionRequest hook (--full) + StopFailure hook (--fallback --model-switch)
python3 smart_confirmer.py --full --setup

# 仅配置权限确认
python3 smart_confirmer.py --hook --ai --allow-all --setup

# 仅配置故障转移
python3 smart_confirmer.py --fallback --setup
```

`--setup` 会自动将 hooks 写入 `~/.claude/settings.json`，保留已有配置（env、plugins 等）。

### 命令行参数 / CLI Arguments

```
python smart_confirmer.py [session] [模式] [选项]
```

| 参数 | 说明 |
|------|------|
| `session` | tmux 会话名（默认 `claude`） |
| **模式（四选一）** | |
| `--tmux` | Tmux 轮询模式：监控屏幕并自动按 Enter 确认 |
| `--hook` | Hook 模式：PermissionRequest 事件处理 |
| `--model-switch` | 模型时间表检查（单独使用时循环；hook 调用时单次检查） |
| `--fallback` | StopFailure 事件：连续失败后切换备用模型 |
| **选项** | |
| `--full` | 等价于 `--hook --ai --allow-all` |
| `--ai` | 启用 AI 兜底（规则不匹配时调用本地模型） |
| `--allow-all` | Hook 模式下全部允许（仍拦截危险命令） |
| `--fallback-threshold N` | 连续失败多少次后切换备用模型（默认 3） |
| `--fallback-reset` | 重置 fallback 失败计数和激活状态 |
| `--setup` | 根据当前参数自动配置 settings.json |

### 常用组合 / Common Combinations

```bash
# 一键配置（推荐）
python3 smart_confirmer.py --full --setup

# Tmux 监控 + AI + 定时切换
python3 smart_confirmer.py claude --tmux --ai --model-switch

# 手动测试 PermissionRequest
echo '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | python3 smart_confirmer.py --hook

# 手动测试 StopFailure + 模型检查
echo '{"error":"rate_limit"}' | python3 smart_confirmer.py --fallback --model-switch

# 重置 fallback 状态
python3 smart_confirmer.py --fallback-reset

# 独立运行模型切换（循环）
nohup python3 smart_confirmer.py claude --model-switch > /tmp/model_switch.log 2>&1 &
```

### Tmux 模式

监控 tmux 会话，自动确认 Claude Code 的权限提示。

```bash
python smart_confirmer.py --tmux claude          # 纯规则
python smart_confirmer.py --tmux claude --ai      # AI 兜底
python smart_confirmer.py --tmux claude --ai --model-switch  # + 定时切换
```

工作流程：`轮询 tmux 屏幕 → 关键词检测 → 规则匹配 → AI 兜底 → 发送 Enter`

- 检测到 `requires approval`、`do you want`、`proceed` 等关键词时触发
- 直接发送 Enter 选中当前高亮选项（`❯`）
- 冷却期内不重复确认，防止误触

### Hook 模式

集成 Claude Code 的 `PermissionRequest` hook，逐条判断工具调用是否允许。

判断优先级：

1. 拒绝规则 — 匹配危险命令则 deny（即使 `--allow-all` 也生效）
2. `--allow-all` — 直接允许所有请求
3. 允许规则 — 匹配安全命令则 allow
4. AI 兜底 — 本地模型判断（需 `--ai`）
5. 无匹配 — 走默认流程

**内置拒绝规则：**

| 模式 | 匹配命令 |
|------|----------|
| `rm\s+-rf\s+/` | `rm -rf /` |
| `:\(\)\{.*:\|:&\}` | Fork 炸弹 |
| `dd\s+if=.*of=/dev/` | `dd` 写设备 |
| `curl\|wget ... \| sh` | 管道执行远程脚本 |
| `mkfs` | 格式化磁盘 |
| `iptables` | 防火墙规则 |
| `chmod\s+-R\s+777\s+/` | 全局写权限 |
| `shutdown\|reboot` | 关机重启 |

`Write`/`Edit` 写入 `/etc/`、`/boot/`、`/sys/`、`/proc/` 路径也会被拦截。

**内置允许规则：**

| 类别 | 规则 |
|------|------|
| 安全工具 | `Read`、`Glob`、`Grep`、`WebSearch`、`WebFetch`、`mcp__*` |
| Git 只读 | `git status`、`git log`、`git diff`、`git branch`、`git show` 等 |
| 系统查看 | `ls`、`cat`、`head`、`tail`、`pwd`、`whoami`、`which`、`echo`、`find` |
| 构建/测试 | `npm test/run/lint/install`、`pytest`、`make` |

### 模型定时切换 (`--model-switch`)

按时间段自动切换 `~/.claude/settings.json` 中的模型配置。

**运行方式：**

| 命令 | 行为 |
|------|------|
| `python3 ... --model-switch` | 独立进程，循环运行（需后台启动） |
| `python3 ... --fallback --model-switch` | StopFailure 触发时单次检查模型时间表 |
| `python3 ... --tmux --model-switch` | 与 Tmux 模式并行，后台守护线程循环 |

与 `--tmux` 并行时，仅在 Claude 空闲时切换，避免打断 API 调用。

### 故障转移 (`--fallback`)

通过 Claude Code 的 `StopFailure` hook 检测 API 错误，连续失败达到阈值后自动切换到备用模型。

- 失败计数持久化到 `.fallback_count` 文件
- 激活状态写入 `.fallback_active` 文件（同时阻止 `--model-switch` 覆盖）
- `PermissionRequest` 成功触发时自动清除失败计数和激活状态（说明模型已恢复）
- 支持多个备用模型，按 `priority` 排序尝试

计入失败数的错误类型：`rate_limit`、`authentication_failed`、`billing_error`、`server_error`、`unknown`

不计入的错误：`max_output_tokens`、`invalid_request`

```bash
# 一键配置（PermissionRequest + StopFailure 含模型检查）
python3 smart_confirmer.py --full --setup

# 手动重置
python3 smart_confirmer.py --fallback-reset
```

### 停止运行 / Stopping

```bash
kill <PID>       # 发送信号停止
touch .stop      # 或创建停止文件（仅 tmux 模式）
```

## 配置 / Configuration

复制 `.env.example` 到 `.env` 并按需修改。

### AI 模型配置（`--ai` 模式生效）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QWEN_API_URL` | `http://192.168.0.70:5564/v1/chat/completions` | 本地 AI API 地址 |
| `QWEN_MODEL` | `/opt/models/Qwen/Qwen3.5-27B-FP8` | 模型名称或路径 |
| `QWEN_TIMEOUT` | `30` | API 请求超时（秒） |

### 通用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COOLDOWN` | `2` | 确认后冷却秒数 |
| `RULE_CONTEXT_SIZE` | `1000` | 规则模式截取屏幕字符数 |
| `AI_CONTEXT_SIZE` | `300` (Tmux) / `1000` (Hook) | 发送给 AI 的字符数 |
| `HEARTBEAT_INTERVAL` | `60` | 心跳输出间隔（秒） |

### Hook 模式配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOOK_ALLOW_PATTERNS` | （空） | 额外允许的命令模式，逗号分隔正则 |
| `HOOK_DENY_PATTERNS` | （空） | 额外拒绝的命令模式，逗号分隔正则 |
| `HOOK_LOG_FILE` | `hook.log` | 日志文件路径 |

### 模型调度配置

`.model_schedules.json` 用于按时间段自动切换不同的 AI 模型供应商。**此文件包含 API Token，已在 `.gitignore` 中排除，请勿提交到仓库。**

| 字段 | 说明 |
|------|------|
| `settings_path` | Claude Code 的 `settings.json` 路径（支持 `~`） |
| `check_interval` | 检查调度间隔（秒） |
| `default` | 默认时段的 API 配置 |
| `schedules` | 调度列表，按时段切换不同供应商 |
| `schedules[].name` | 调度名称（仅用于日志） |
| `schedules[].start` | 开始时间（HH:MM） |
| `schedules[].end` | 结束时间（HH:MM） |
| `schedules[].env` | 该时段的 API 配置 |
| `fallback_models` | 备用模型列表，按 `priority` 排序 |

`default`、`schedules[].env`、`fallback_models[].env` 中的环境变量：

| 变量 | 说明 |
|------|------|
| `ANTHROPIC_BASE_URL` | API 基础地址 |
| `ANTHROPIC_AUTH_TOKEN` | API 认证 Token |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | Haiku 模型名称 |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Sonnet 模型名称 |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Opus 模型名称 |

## 架构 / Architecture

单文件应用 `smart_confirmer.py`，四个核心类：

- **`FixConfirmer`** — Tmux 轮询模式，持续监控屏幕并自动确认
- **`HookHandler`** — Hook 模式，接收 stdin JSON 做实时 allow/deny 决策
- **`FallbackHandler`** — 故障转移，连续失败后切换备用模型
- **`ModelSwitcher`** — 定时切换，按时间段切换模型供应商

## 许可 / License

MIT
