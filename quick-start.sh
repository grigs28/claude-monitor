#!/bin/bash
# 快速启动 Claude 自动确认器

SESSION_NAME=${1:-claude}

echo "=========================================="
echo "Claude 自动确认器 - 快速启动"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  ./quick-start.sh              # 监控 'claude' 会话"
echo "  ./quick-start.sh mysession    # 监控指定会话"
echo ""
echo "[1] 检查 tmux 会话..."
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "  ✓ 会话 '$SESSION_NAME' 存在"
else
    echo "  ✗ 会话 '$SESSION_NAME' 不存在"
    echo ""
    echo "请先创建并启动 Claude Code:"
    echo "  tmux new-session -s $SESSION_NAME"
    echo "  conda activate taf"
    echo "  cd /mnt/SSD/webapp/TAF"
    echo "  claude"
    echo ""
    exit 1
fi

echo ""
echo "[2] 启动自动确认器..."
echo "  会话名: $SESSION_NAME"
echo "  按 Ctrl+C 停止"
echo ""
echo "=========================================="
echo ""

# 启动确认器
python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py "$SESSION_NAME"
