# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Monitor（智能确认器）是一个自动化工具，用于监控 tmux 中运行的 Claude Code 会话，自动响应权限确认提示（如 "This command requires approval"、"Do you want to proceed"）。

## Running

```bash
# 纯规则模式（无需AI）
python smart_confirmer.py claude

# AI 兜底模式（规则优先，不认识时调用本地 Qwen 模型）
python smart_confirmer.py claude --ai

# 指定 tmux 会话名
python smart_confirmer.py my_session --ai
```

## Dependencies

- `requests` — AI 模式下调用 API
- `python-dotenv` — 加载 `.env` 配置（可选，缺失时使用默认值）
- `tmux` — 必须可用，用于捕获屏幕和发送按键

## Architecture

单文件应用 `smart_confirmer.py`，核心类 `FixConfirmer`：

1. **监控循环** (`run`) — 持续轮询 tmux 屏幕内容，带 2 秒冷却期防止重复确认
2. **屏幕捕获** (`get_screen`) — 通过 `tmux capture-pane` 获取最后 1000 字符
3. **规则判断** (`should_confirm`) — 关键词匹配（`requires approval`、`do you want`、`proceed`），优先选 "always allow"（选项2），否则选 "Yes"（选项1）
4. **AI 兜底** (`ask_ai`) — 规则不认识时调用本地 Qwen API 判断
5. **按键发送** (`send`) — 通过 `tmux send-keys` 发送选项编号 + Enter

判断优先级：规则匹配 → AI 兜底（需 `--ai`）→ 跳过

## Configuration

通过 `.env` 文件配置（参考 `.env.example`）：

```ini
QWEN_API_URL=http://192.168.0.70:5564/v1/chat/completions  # 本地 AI API
QWEN_MODEL=/opt/models/Qwen/Qwen3.5-27B-FP8               # 模型路径
QWEN_TIMEOUT=60                                             # API 超时秒数
```

## Archive

`.archive/` 目录包含历史迭代版本（多种确认器实现），当前活跃版本为 `smart_confirmer.py`。
