# Claude 自动确认器 - 项目说明

## 项目地址
- **GitHub**: https://github.com/grigs28/claude-monitor
- **本地**: `/mnt/SSD/opt/claude-monitor/`

## 主要文件
- `smart_confirmer.py` - 智能确认器（推荐，支持规则和 AI 两种模式）
- `claude-auto-confirm.py` - 基础确认器（带历史记录，只有规则模式）
- `simple_rule_confirmer.py` - 简单规则确认器（只有规则模式）
- `confirm_history.py` - 确认历史管理模块

## 功能
- 自动监控 tmux 会话中的 Claude Code
- 检测并自动确认各种提示
- 支持规则模式和 AI 模式
- 内容哈希去重，避免重复确认

## 使用方法
```bash
# 规则模式（默认，快速）
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py claude

# AI 模式（智能判断）
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py claude --ai
```

## 最新更新
- 2026-03-29 15:30: 修复变量名 bug
- 添加页面静止检测
- 优化输出频率，减少 CPU 占用

---
_其他项目记录在 MEMORY.md_
