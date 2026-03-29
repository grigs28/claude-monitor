# Claude Code Auto Confirmer

中英文说明 | [English](#english) | [中文](#chinese)

---

<a name="english"></a>
## English

Automatically monitor and confirm Claude Code prompts, making your AI programming assistant more automated.

### Quick Start

```bash
# Rule mode (fast, default)
python3 smart_confirmer.py claude

# AI mode (intelligent)
python3 smart_confirmer.py claude --ai
```

### Features

- ✅ Dual mode: Rule-based (fast) or AI-powered (smart)
- ✅ Auto-detect confirmation prompts
- ✅ Prioritize "always allow" options
- ✅ Prevent duplicate confirmations
- ✅ Skip command line prompts

### Requirements

- tmux
- Python 3.7+
- For AI mode: Local Qwen 3.5 API access

### Usage

1. Start Claude Code in tmux
2. Run the confirmer in another terminal
3. All confirmations will be handled automatically!

### Files

```
smart_confirmer.py       # ⭐ Smart confirmer (recommended)
claude-auto-confirm.py   # Basic confirmer (with history)
simple_rule_confirmer.py # Simple rule-based confirmer
confirm_history.py       # History tracking module
```

---

<a name="chinese"></a>
## 中文

自动监控并确认 Claude Code 的各种提示，让你的 AI 编程助手更加自动化。

### 快速开始

```bash
# 规则模式（快速，默认）
python3 smart_confirmer.py claude

# AI 模式（智能）
python3 smart_confirmer.py claude --ai
```

### 特性

- ✅ 双模式：规则模式（快速）或 AI 模式（智能）
- ✅ 自动检测确认提示
- ✅ 优先选择"永久允许"选项
- ✅ 防止重复确认
- ✅ 自动跳过命令行提示

### 系统要求

- tmux
- Python 3.7+
- AI 模式需要：本地 Qwen 3.5 API 访问

### 使用方法

1. 在 tmux 中启动 Claude Code
2. 在另一个终端运行确认器
3. 所有确认将自动处理！

### 文件说明

```
smart_confirmer.py       # ⭐ 智能确认器（推荐）
claude-auto-confirm.py   # 基础确认器（带历史）
simple_rule_confirmer.py # 简单规则确认器
confirm_history.py       # 历史记录模块
```

---

## License

MIT License
