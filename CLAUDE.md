# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart Confirmer (智能确认器) — 自动监控 Claude Code 会话，响应权限确认、按时间段切换模型、API 故障转移。单文件应用 `smart_confirmer.py`，零测试框架，通过手动 echo-pipe 测试。

## Running

```bash
# 一键配置（写入 ~/.claude/settings.json hooks）
python3 smart_confirmer.py --full --setup

# Tmux 模式（轮询屏幕自动确认）
python3 smart_confirmer.py claude --tmux --ai

# Hook 模式（由 Claude Code 自动调用）
python3 smart_confirmer.py --full

# 手动测试 Hook
echo '{"tool_name":"Bash","tool_input":{"command":"git status"}}' | python3 smart_confirmer.py --hook

# 手动测试 Fallback
echo '{"error":"rate_limit"}' | python3 smart_confirmer.py --fallback

# 重置 fallback 状态
python3 smart_confirmer.py --fallback-reset
```

## CLI Arguments

| 参数 | 说明 |
|------|------|
| `session` | tmux 会话名（默认 `claude`） |
| `--tmux` | Tmux 轮询模式 |
| `--hook` | PermissionRequest Hook 模式 |
| `--model-switch` | 模型时间表检查（单独=循环；hook 调用=单次） |
| `--fallback` | StopFailure 连续失败后切换备用模型 |
| `--full` | 等价于 `--hook --ai --allow-all`（`--setup` 时安装 3 个 hook：PermissionRequest→`--full`、StopFailure→`--fallback`、Stop→`--model-switch`） |
| `--ai` | AI 兜底（规则不匹配时调本地模型） |
| `--allow-all` | Hook 模式全部允许（仍拦截危险命令） |
| `--setup` | 自动配置 settings.json hooks |
| `--fallback-threshold N` | 失败阈值（默认 3） |
| `--fallback-reset` | 重置 fallback 状态 |

## Architecture

单文件 `smart_confirmer.py`，四个核心类：

1. **`FixConfirmer`** (L25) — Tmux 轮询：`get_screen()` → `detect()` 关键词 → `should_confirm()` 规则+AI → `send()` Enter
2. **`HookHandler`** (L219) — PermissionRequest hook：stdin JSON → `check_deny()` → `--allow-all` → `check_allow()` → `_ai_decide()` → stdout JSON
3. **`FallbackHandler`** (L454) — StopFailure hook：累计失败计数 → 达阈值先尝试 schedule/default 模型 → 再尝试 `fallback_models` 按优先级排序
4. **`ModelSwitcher`** (L613, `threading.Thread`) — 后台线程：`_get_schedule_env()` 匹配当前时段 → `_is_claude_idle()` 检查 → `_do_switch()` 写 settings.json

决策优先级（Hook 模式）：拒绝规则 > allow-all > 允许规则 > AI 兜底 > 默认流程

关键机制：
- `.fallback_active` 文件存在时，ModelSwitcher 跳过切换，FallbackHandler 不重复切换
- PermissionRequest allow 时自动清除 `.fallback_count` 和 `.fallback_active`
- `_get_schedule_env()` 支持跨午夜时段（如 22:00-06:00）
- ModelSwitcher 检测 Claude 进程是否存在（`pgrep -f claude`），进程消失则自动退出
- `--setup` 保留 settings.json 中已有的 env、plugins 等配置

## Configuration

`.env` — AI API 地址/超时、冷却时间、上下文大小、自定义允许/拒绝正则
`.model_schedules.json` — settings_path、check_interval、default、schedules[]、fallback_models[]（含 API Token，已 gitignore）

## Dependencies

- `requests` — AI 模式调用 API
- `python-dotenv` — 加载 `.env`（可选，缺失时静默跳过）
- `tmux` — Tmux 模式必需

## Stopping

```bash
kill <PID>       # 发送信号
touch .stop      # 创建停止文件（仅 tmux 模式）
```
