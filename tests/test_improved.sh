#!/bin/bash
# 改进的测试：模拟真实的 Claude Code 确认提示

SESSION_NAME="claude-test-improved"

echo "=========================================="
echo "改进的确认提示测试"
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

echo "[2] 模拟真实的 Claude Code 确认提示..."
# 清屏
tmux send-keys -t "$SESSION_NAME" 'clear' Enter
sleep 0.5

# 模拟创建目录的场景
tmux send-keys -t "$SESSION_NAME" 'printf "mkdir 123\n"' Enter
tmux send-keys -t "$SESSION_NAME" 'printf "   Create directory 123\n"' Enter
tmux send-keys -t "$SESSION_NAME" 'printf "\n"' Enter
tmux send-keys -t "$SESSION_NAME" 'printf " Do you want to proceed?\n"' Enter
tmux send-keys -t "$SESSION_NAME" 'printf " ❯ 1. Yes\n"' Enter
tmux send-keys -t "$SESSION_NAME" 'printf "   2. Yes, and always allow access to 123/ from this project\n"' Enter
tmux send-keys -t "$SESSION_NAME" 'printf "   3. No\n"' Enter

sleep 2

echo "  ✓ 确认提示已显示"
echo ""

echo "[3] 当前会话内容："
tmux capture-pane -t "$SESSION_NAME" -p | tail -15
echo ""

echo "[4] 启动自动确认器..."
echo "  等待 10 秒观察行为..."
timeout 12 python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py "$SESSION_NAME" 2>&1 &
MONITOR_PID=$!

sleep 10

echo ""
echo "[5] 检查结果："
RESULT=$(tmux capture-pane -t "$SESSION_NAME" -p | tail -20)
echo "$RESULT"
echo ""

# 分析结果
if echo "$RESULT" | grep -q "^[12]"; then
    echo "❌ 失败：确认器在命令行误发送了按键"
elif echo "$RESULT" | grep -q "2.*Yes, and always allow"; then
    echo "✅ 成功：确认器正确发送了按键 2"
else
    echo "⚠️  不确定：请手动检查结果"
fi

echo ""
echo "=========================================="
