# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Monitor（智能确认器）是一个自动化工具，用于监控 tmux 中运行的 Claude Code 会话，自动响应权限确认提示。

## Running

```bash
# 一键配置（推荐，写入 settings.json）
python3 smart_confirmer.py --full --fallback --setup

# Tmux 模式
python3 smart_confirmer.py claude --tmux --ai

# Hook 模式（由 Claude Code 自动调用）
python3 smart_confirmer.py --full

# 独立模型切换
python3 smart_confirmer.py claude --model-switch
```

## CLI Arguments

| 参数 | 说明 |
|------|------|
| `--tmux` | Tmux 轮询模式 |
| `--hook` | PermissionRequest Hook 模式 |
| `--model-switch` | 模型定时切换 |
| `--fallback` | StopFailure 连续失败后切换备用模型 |
| `--full` | 等价于 `--hook --ai --allow-all --model-switch` |
| `--ai` | AI 兜底 |
| `--allow-all` | 全部允许（仍拦截危险命令） |
| `--setup` | 自动配置 settings.json |
| `--fallback-threshold N` | 失败阈值（默认 3） |
| `--fallback-reset` | 重置 fallback 状态 |

## Dependencies

- `requests` — AI 模式下调用 API
- `python-dotenv` — 加载 `.env` 配置（可选）
- `tmux` — Tmux 模式必需

## Architecture

单文件应用 `smart_confirmer.py`，四个核心类：

1. **`FixConfirmer`** — Tmux 轮询，监控屏幕自动确认
2. **`HookHandler`** — PermissionRequest hook，规则 + AI allow/deny
3. **`FallbackHandler`** — StopFailure hook，连续失败后切换备用模型（3 次阈值，文件持久化）
4. **`ModelSwitcher`** — 后台线程，按时间段切换模型（仅在 Claude 空闲时）

关键机制：
- `.fallback_active` 文件存在时，ModelSwitcher 跳过切换
- PermissionRequest 成功触发时自动清除 fallback 状态
- `.model_schedules.json` 统一管理 default/schedules/fallback_models 配置

## Configuration

`.env` — AI API、冷却时间、上下文大小等
`.model_schedules.json` — 模型调度 + 备用模型（含 API Token，已在 .gitignore 中）
