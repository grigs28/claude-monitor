#!/bin/bash
# 模拟 Claude Code 确认提示的测试脚本
# 用于测试 claude-confirm.py 的检测能力

SESSION_NAME=${1:-claude-test}

echo "=========================================="
echo "Claude Code 确认提示模拟器"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  ./simulate_confirm.sh [会话名]"
echo ""
echo "这个脚本会在 tmux 会话中模拟各种 Claude Code 的确认提示"
echo ""

# 检查 tmux 是否可用
if ! command -v tmux &> /dev/null; then
    echo "错误: tmux 未安装"
    exit 1
fi

# 创建或连接到会话
echo "[1] 创建测试会话: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME" -n test 2>/dev/null || true

sleep 1

echo "[2] 模拟场景列表:"
echo ""
echo "  A. 编辑确认提示"
echo "  B. 继续操作提示"
echo "  C. 运行命令提示"
echo "  D. 菜单选择提示"
echo "  E. 混合场景"
echo "  Q. 退出"
echo ""

read -p "选择场景 (A-E/Q): " choice

case "$choice" in
    [Aa])
        echo "[场景] 模拟编辑确认..."
        tmux send-keys -t "$SESSION_NAME" 'echo "Do you want to make this edit to CLAUDE.md?"' Enter
        tmux send-keys -t "$SESSION_NAME" 'echo "❯ 1. Yes / 2. Yes, allow all edits / 3. No"' Enter
        ;;
    [Bb])
        echo "[场景] 模拟继续操作..."
        tmux send-keys -t "$SESSION_NAME" 'echo "Do you want to proceed? [Y/n]"' Enter
        ;;
    [Cc])
        echo "[场景] 模拟运行命令..."
        tmux send-keys -t "$SESSION_NAME" 'echo "Run bash script? [1. Yes / 2. No]"' Enter
        ;;
    [Dd])
        echo "[场景] 模拟菜单选择..."
        tmux send-keys -t "$SESSION_NAME" 'echo "Select an option:"' Enter
        tmux send-keys -t "$SESSION_NAME" 'echo "❯ 1. Option A"' Enter
        tmux send-keys -t "$SESSION_NAME" 'echo "  2. Option B"' Enter
        ;;
    [Ee])
        echo "[场景] 混合场景..."
        tmux send-keys -t "$SESSION_NAME" 'echo "Claude Code is thinking..."' Enter
        sleep 1
        tmux send-keys -t "$SESSION_NAME" 'echo "Do you want to make this edit to test.py?"' Enter
        tmux send-keys -t "$SESSION_NAME" 'echo "❯ 1. Yes / 2. Yes, allow all edits / 3. No"' Enter
        ;;
    [Qq])
        echo "[退出] 清理会话..."
        tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
        echo "完成"
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "[3] 提示已显示在会话 '$SESSION_NAME' 中"
echo ""
echo "现在可以运行确认器进行测试:"
echo "  python3 /mnt/SSD/opt/claude-monitor/claude-confirm.py $SESSION_NAME"
echo ""
echo "查看会话内容:"
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "清理会话:"
echo "  tmux kill-session -t $SESSION_NAME"
