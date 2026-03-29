#!/bin/bash
# 改进的测试：直接显示确认提示文本

SESSION_NAME="claude-test-improved"

echo "=========================================="
echo "Claude 自动确认器 - 改进测试"
echo "=========================================="
echo ""

cleanup() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    pkill -f "claude-auto-confirm.py" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "[1] 创建测试会话..."
tmux new-session -d -s "$SESSION_NAME"
sleep 1

echo "[2] 显示确认提示（使用 printf）..."
# 使用 printf 确保提示停留在屏幕上
tmux send-keys -t "$SESSION_NAME" "printf '\n'" Enter
tmux send-keys -t "$SESSION_NAME" "printf 'mkdir 123\n'" Enter
tmux send-keys -t "$SESSION_NAME" "printf '   Create directory 123\n'" Enter
tmux send-keys -t "$SESSION_NAME" "printf '\n'" Enter
tmux send-keys -t "$SESSION_NAME" "printf ' Do you want to proceed?\n'" Enter
tmux send-keys -t "$SESSION_NAME" "printf ' ❯ 1. Yes\n'" Enter
tmux send-keys -t "$SESSION_NAME" "printf '   2. Yes, and always allow access to 123/ from this project\n'" Enter
tmux send-keys -t "$SESSION_NAME" "printf '   3. No\n'" Enter

sleep 2

echo "[3] 当前会话内容："
tmux capture-pane -t "$SESSION_NAME" -p | tail -15
echo ""

echo "[4] 启动确认器（后台运行 10 秒）..."
timeout 10 python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py "$SESSION_NAME" 2>&1 | head -20 &
MONITOR_PID=$!

sleep 10

echo ""
echo "[5] 测试结果："
echo ""
echo "=== tmux 会话内容 ==="
tmux capture-pane -t "$SESSION_NAME" -p | tail -20
echo ""

# 检查是否发送了按键
RESULT=$(tmux capture-pane -t "$SESSION_NAME" -p)
if echo "$RESULT" | grep -q "^2"; then
    echo "✅ 成功！确认器发送了按键 '2'"
elif echo "$RESULT" | grep -q "^1"; then
    echo "✅ 成功！确认器发送了按键 '1'"
else
    echo "❌ 失败！确认器没有发送按键"
    echo ""
    echo "调试信息："
    echo "- 确认器进程："
    ps aux | grep "claude-auto-confirm" | grep -v grep || echo "  未运行"
fi

echo ""
echo "=========================================="
