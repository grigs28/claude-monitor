# 智能确认器 / Smart Confirmer

自动监控 [Claude Code](https://claude.ai/code) 会话，实时响应权限确认提示。

支持两种模式：
- **Tmux 模式** (`--tmux`) — 轮询 tmux 屏幕内容，自动点击确认按钮
- **Hook 模式** (`--hook`) — 集成 Claude Code `PermissionRequest` hook，实时 allow/deny

判断策略：**规则优先 → AI 兜底**。规则匹配常见场景零延迟，未命中的交给本地 Qwen 模型判断。

> **建议使用本地部署的 AI 模型**（如 Qwen、LLaMA 等），避免调用云端 API 产生不必要的费用。

## 功能特点

- 规则优先，AI 兜底（`--ai` 开启）
- Hook 模式支持 `--allow-all` 全部允许
- 内置危险命令拦截（`rm -rf /`、`dd`、`mkfs`、`fork 炸弹` 等）
- 内置安全命令白名单（`git status`、`ls`、`pytest`、`Read`/`Glob`/`Grep` 等）
- 纯规则模式零依赖（仅需 tmux）；AI 模式额外需要 `requests`
- `.env` 文件配置，支持自定义允许/拒绝规则
- 单文件应用，开箱即用

## 快速开始

### 前置条件

- Python 3.8+
- tmux（Tmux 模式必需）
- 可选：本地 LLM API（如 Qwen），用于 AI 兜底

```bash
# 安装依赖（可选，仅 --ai 模式需要）
pip install requests python-dotenv
```

### 命令行参数

```
python smart_confirmer.py --tmux [会话名] [--ai]
python smart_confirmer.py --hook [--ai] [--allow-all]
```

| 参数 | 说明 |
|------|------|
| `session` | tmux 会话名（默认 `claude`） |
| `--tmux` | Tmux 轮询模式：监控屏幕并自动确认提示 |
| `--hook` | Hook 模式：PermissionRequest 事件处理 |
| `--ai` | 启用 AI 兜底（规则不匹配时调用本地模型） |
| `--allow-all` | Hook 模式下全部允许（跳过所有规则检查） |

### Tmux 模式

监控 tmux 会话，自动确认 Claude Code 的权限提示：

```bash
# 纯规则模式（无需 AI）
python smart_confirmer.py --tmux claude

# AI 兜底模式（规则优先，未命中时调用本地模型）
python smart_confirmer.py --tmux claude --ai

# 指定 tmux 会话名
python smart_confirmer.py --tmux my_session --ai
```

工作流程：

```
轮询 tmux 屏幕 → 关键词检测 → 规则匹配 → AI 兜底 → 发送按键
```

- 检测到 `requires approval`、`do you want`、`proceed` 等关键词时触发
- 优先选 "always allow"（选项 2），否则选 "Yes"（选项 1）
- 冷却期内不重复确认，防止误触

### Hook 模式

集成 Claude Code 的 `PermissionRequest` hook，逐条判断工具调用是否允许。

**基础用法** — 规则判断 allow/deny：

在 Claude Code 的 `settings.json` 中配置：

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

**全部允许** — 跳过所有检查，直接 allow（适合可信环境）：

```json
"command": "python3 /path/to/smart_confirmer.py --hook --allow-all"
```

**AI 兜底** — 规则不匹配时交给本地模型判断：

```json
"command": "python3 /path/to/smart_confirmer.py --hook --ai"
```

**手动测试**：

```bash
# 测试允许规则（git status 应该被允许）
echo '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | python3 smart_confirmer.py --hook

# 测试拒绝规则（rm -rf 应该被拒绝）
echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | python3 smart_confirmer.py --hook

# 测试全部允许
echo '{"tool_name":"Bash","tool_input":{"command":"anything"}}' | python3 smart_confirmer.py --hook --allow-all
```

工作流程：

```
stdin JSON → 全部允许? → 拒绝规则 → 允许规则 → AI 兜底 → stdout JSON
```

**判断优先级：**
1. `--allow-all` — 直接允许所有请求
2. 拒绝规则 — 匹配危险命令则 deny
3. 允许规则 — 匹配安全命令则 allow
4. AI 兜底 — 本地模型判断（需 `--ai`）
5. 无匹配 — 走默认流程

**内置拒绝规则（即使 `--allow-all` 之外也会拦截）：**

| 模式 | 匹配命令 |
|------|---------|
| `rm\s+-rf\s+/` | `rm -rf /` |
| `:\(\)\{.*:\|:&\}` | Fork 炸弹 |
| `dd\s+if=.*of=/dev/` | `dd` 写设备 |
| `curl\|wget ... \| sh` | 管道执行远程脚本 |
| `mkfs` | 格式化磁盘 |
| `iptables` | 防火墙规则 |
| `chmod\s+-R\s+777\s+/` | 全局写权限 |
| `shutdown\|reboot` | 关机重启 |

另外，`Write`/`Edit` 写入 `/etc/`、`/boot/`、`/sys/`、`/proc/` 路径也会被拦截。

**内置允许规则：**

| 类别 | 规则 |
|------|------|
| 安全工具 | `Read`、`Glob`、`Grep`、`WebSearch`、`WebFetch`、`mcp__*` |
| Git 只读 | `git status`、`git log`、`git diff`、`git branch`、`git show` 等 |
| 系统查看 | `ls`、`cat`、`head`、`tail`、`pwd`、`whoami`、`which`、`echo`、`find` |
| 构建/测试 | `npm test/run/lint/install`、`pytest`、`make` |

### 停止运行

```bash
# 发送信号停止
kill <PID>

# 或创建停止文件
touch .stop
```

## 配置

复制 `.env.example` 到 `.env` 并按需修改：

```bash
cp .env.example .env
```

### AI 模型配置（`--ai` 模式生效）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QWEN_API_URL` | `http://192.168.0.70:5564/v1/chat/completions` | 本地 AI API 地址 |
| `QWEN_MODEL` | `/opt/models/Qwen/Qwen3.5-27B-FP8` | 模型名称或路径 |
| `QWEN_TIMEOUT` | `30` | API 请求超时（秒） |

### 通用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COOLDOWN` | `2` | 确认后冷却秒数，防止重复触发 |
| `RULE_CONTEXT_SIZE` | `1000` | 规则模式截取屏幕字符数 |
| `AI_CONTEXT_SIZE` | `300`（Tmux）/ `1000`（Hook） | 发送给 AI 的字符数 |
| `HEARTBEAT_INTERVAL` | `60` | 无事件时心跳输出间隔（秒） |

### Hook 模式配置（`--hook` 模式生效）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOOK_ALLOW_PATTERNS` | （空） | 额外允许的命令模式，逗号分隔正则 |
| `HOOK_DENY_PATTERNS` | （空） | 额外拒绝的命令模式，逗号分隔正则 |
| `HOOK_LOG_FILE` | `hook.log` | 日志文件路径 |

自定义规则示例：

```ini
# 允许 docker compose 相关命令
HOOK_ALLOW_PATTERNS=docker\s+compose\s+up,docker\s+compose\s+down

# 拒绝生产环境部署
HOOK_DENY_PATTERNS=deploy\s+--prod,kubectl\s+apply
```

## 架构

单文件应用 `smart_confirmer.py`，两个核心类：

- **`FixConfirmer`** — Tmux 轮询模式，持续监控屏幕并自动确认
- **`HookHandler`** — Hook 模式，接收 stdin JSON 做实时 allow/deny 决策

## 许可

MIT
# claude-monitor
