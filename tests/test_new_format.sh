#!/bin/bash
# 测试新的目录访问确认格式

SESSION_NAME="claude-test-new"

echo "=========================================="
echo "测试新的确认格式"
echo "=========================================="
echo ""

# 清理
cleanup() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    pkill -f "claude-auto-confirm.py" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

# 创建测试会话
echo "[1] 创建测试会话..."
tmux new-session -d -s "$SESSION_NAME"
sleep 1

# 显示新的确认格式
echo "[2] 模拟新的确认提示..."
tmux send-keys -t "$SESSION_NAME" 'clear' Enter
tmux send-keys -t "$SESSION_NAME" 'cat << EOF' Enter
tmux send-keys -t "$SESSION_NAME" 'mkdir 123' Enter
tmux send-keys -t "$SESSION_NAME" '   Create directory 123' Enter
tmux send-keys -t "$SESSION_NAME" '' Enter
tmux send-keys -t "$SESSION_NAME" ' Do you want to proceed?' Enter
tmux send-keys -t "$SESSION_NAME" ' ❯ 1. Yes' Enter
tmux send-keys -t "$SESSION_NAME" '   2. Yes, and always allow access to 123/ from this project' Enter
tmux send-keys -t "$SESSION_NAME" '   3. No' Enter
tmux send-keys -t "$SESSION_NAME" 'EOF' Enter

sleep 2

echo "  ✓ 确认提示已显示"
echo ""

# 显示当前内容
echo "[3] 当前会话内容："
tmux capture-pane -t "$SESSION_NAME" -p | tail -15
echo ""

# 启动确认器
echo "[4] 启动自动确认器..."
timeout 10 python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py "$SESSION_NAME" 2>&1 &
MONITOR_PID=$!

echo "  ✓ 确认器已启动 (PID: $MONITOR_PID)"
echo ""

# 等待并观察
echo "[5] 观察 8 秒..."
for i in {1..8}; do
    sleep 1
    echo -n "."
done
echo ""
echo ""

# 检查结果
echo "[6] 检查结果："
RESULT=$(tmux capture-pane -t "$SESSION_NAME" -p | tail -15)
echo "$RESULT"
echo ""

# 检查是否发送了按键
if echo "$RESULT" | grep -q "^[12]"; then
    echo "✅ 成功！确认器检测到了新格式并发送了按键"
else
    echo "❌ 失败！确认器没有发送按键"
    echo ""
    echo "调试信息："
    echo "- 检查确认器是否正在运行："
    ps aux | grep "claude-auto-confirm" | grep -v grep || echo "  确认器未运行"
fi

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
