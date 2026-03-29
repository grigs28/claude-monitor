#!/bin/bash
# Claude 自动确认器 - 完整测试流程
# 这个脚本会：
# 1. 启动一个 Claude Code 会话
# 2. 启动自动确认器监控
# 3. 模拟各种操作触发确认提示
# 4. 验证确认器是否自动处理

set -e

SESSION_NAME="claude-test"
MONITOR_SCRIPT="/mnt/SSD/opt/claude-monitor/claude-auto-confirm.py"
TEST_DIR="/mnt/SSD/opt/claude-monitor/tests"
WORK_DIR="/tmp/claude-test-$$"

echo "=========================================="
echo "Claude 自动确认器 - 完整测试"
echo "=========================================="
echo ""

# 清理函数
cleanup() {
    echo ""
    echo "[清理] 停止所有测试进程..."

    # 关闭 tmux 会话
    tmux has-session -t "$SESSION_NAME" 2>/dev/null && \
        tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

    # 删除测试目录
    rm -rf "$WORK_DIR" 2>/dev/null || true

    # 杀死可能残留的确认器进程
    pkill -f "claude-auto-confirm.py" 2>/dev/null || true

    echo "[清理] 完成"
}

# 设置退出时清理
trap cleanup EXIT INT TERM

# 检查依赖
echo "[1] 检查依赖..."
if ! command -v tmux &> /dev/null; then
    echo "错误: tmux 未安装"
    exit 1
fi

if ! command -v conda &> /dev/null; then
    echo "错误: conda 未安装"
    exit 1
fi

if [ ! -f "$MONITOR_SCRIPT" ]; then
    echo "错误: 确认器脚本不存在: $MONITOR_SCRIPT"
    exit 1
fi

echo "  ✓ tmux: $(which tmux)"
echo "  ✓ conda: $(which conda)"
echo "  ✓ 确认器: $MONITOR_SCRIPT"
echo ""

# 创建测试目录
echo "[2] 创建测试环境..."
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 创建一个简单的 Python 文件用于测试
cat > test_script.py << 'EOF'
#!/usr/bin/env python3
"""测试脚本"""
print("Hello from Claude Code!")
EOF

echo "  ✓ 测试目录: $WORK_DIR"
echo ""

# 启动 tmux 会话并运行 Claude Code
echo "[3] 启动 Claude Code 会话..."
echo "  会话名: $SESSION_NAME"

tmux new-session -d -s "$SESSION_NAME" -n claude

# 等待会话启动
sleep 1

# 在 tmux 中激活环境并启动 Claude
tmux send-keys -t "$SESSION_NAME" "conda activate taf" Enter
sleep 1
tmux send-keys -t "$SESSION_NAME" "cd $WORK_DIR" Enter
sleep 1
tmux send-keys -t "$SESSION_NAME" "claude" Enter

echo "  ✓ Claude Code 已启动"
echo ""
sleep 2

# 启动自动确认器
echo "[4] 启动自动确认器..."
python3 "$MONITOR_SCRIPT" "$SESSION_NAME" > "$WORK_DIR/monitor.log" 2>&1 &
MONITOR_PID=$!

echo "  ✓ 确认器已启动 (PID: $MONITOR_PID)"
echo "  日志文件: $WORK_DIR/monitor.log"
echo ""

# 等待确认器连接
sleep 2

# 发送测试指令
echo "[5] 发送测试指令..."
echo "  指令: '请编辑 test_script.py 文件，在末尾添加一行注释'"
echo ""

tmux send-keys -t "$SESSION_NAME" "请编辑 test_script.py 文件，在末尾添加一行注释" Enter

# 观察一段时间
echo "[6] 观察 Claude Code 和确认器的行为..."
echo "  等待 10 秒..."
echo ""

for i in {1..10}; do
    sleep 1
    echo -n "."
done

echo ""
echo ""

# 检查结果
echo "[7] 检查结果..."
echo ""

# 检查 monitor 日志
if [ -f "$WORK_DIR/monitor.log" ]; then
    echo "=== 确认器日志 ==="
    tail -20 "$WORK_DIR/monitor.log"
    echo ""
fi

# 捕获 tmux 会话内容
echo "=== tmux 会话内容（最后 30 行）==="
tmux capture-pane -t "$SESSION_NAME" -p | tail -30
echo ""

# 检查文件是否被修改
if [ -f "$WORK_DIR/test_script.py" ]; then
    echo "=== test_script.py 内容 ==="
    cat "$WORK_DIR/test_script.py"
    echo ""
fi

echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "观察要点："
echo "1. 确认器是否检测到确认提示"
echo "2. 确认器是否自动发送了确认按键"
echo "3. Claude Code 是否成功编辑了文件"
echo ""
echo "如果没有看到自动确认，请检查："
echo "1. Claude Code 的确认提示文本格式"
echo "2. 确认器的日志输出"
echo "3. tmux 会话名是否正确"
echo ""
echo "查看完整日志："
echo "  cat $WORK_DIR/monitor.log"
echo ""
echo "手动查看会话："
echo "  tmux attach -t $SESSION_NAME"
echo "  （按 Ctrl+B 然后 D 分离）"
echo ""

# 保持会话打开以便手动检查
echo "按回车键关闭测试会话..."
read
