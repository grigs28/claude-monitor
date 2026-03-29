#!/bin/bash
# 简化测试：只模拟确认提示，不启动 Claude Code

SESSION_NAME="claude-simple-test"
MONITOR_SCRIPT="/mnt/SSD/opt/claude-monitor/claude-auto-confirm.py"

echo "=========================================="
echo "Claude 自动确认器 - 简化测试"
echo "=========================================="
echo ""

# 清理函数
cleanup() {
    echo ""
    echo "[清理] 停止测试会话..."
    tmux has-session -t "$SESSION_NAME" 2>/dev/null && \
        tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    pkill -f "claude-auto-confirm.py" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# 创建测试会话
echo "[1] 创建测试会话: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME"
sleep 1

# 在会话中显示模拟的确认提示
echo "[2] 显示模拟确认提示..."
tmux send-keys -t "$SESSION_NAME" 'clear' Enter
tmux send-keys -t "$SESSION_NAME" 'echo "=== Claude Code 确认提示模拟 ==="' Enter
tmux send-keys -t "$SESSION_NAME" 'echo ""' Enter
sleep 1

# 显示编辑确认提示
tmux send-keys -t "$SESSION_NAME" 'cat << EOF' Enter
tmux send-keys -t "$SESSION_NAME" 'Do you want to make this edit to test.py?' Enter
tmux send-keys -t "$SESSION_NAME" '' Enter
tmux send-keys -t "$SESSION_NAME" '❯ 1. Yes' Enter
tmux send-keys -t "$SESSION_NAME" '  2. Yes, allow all edits' Enter
tmux send-keys -t "$SESSION_NAME" '  3. No' Enter
tmux send-keys -t "$SESSION_NAME" 'EOF' Enter

sleep 1

echo "  ✓ 确认提示已显示"
echo ""

# 启动确认器
echo "[3] 启动自动确认器..."
python3 "$MONITOR_SCRIPT" "$SESSION_NAME" &
MONITOR_PID=$!

echo "  ✓ 确认器已启动 (PID: $MONITOR_PID)"
echo ""

# 观察
echo "[4] 观察 10 秒..."
for i in {1..10}; do
    sleep 1
    echo -n "."
done
echo ""
echo ""

# 显示结果
echo "[5] 测试结果"
echo ""
echo "=== tmux 会话内容 ==="
tmux capture-pane -t "$SESSION_NAME" -p
echo ""

echo "=========================================="
echo "测试说明"
echo "=========================================="
echo ""
echo "如果确认器工作正常，你应该看到："
echo "1. 会话中出现了 '1' 字符（确认器发送的按键）"
echo "2. 确认器在终端输出了检测和确认的消息"
echo ""
echo "手动查看会话："
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "按回车键退出..."
read
