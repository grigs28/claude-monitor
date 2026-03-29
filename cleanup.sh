#!/bin/bash
# 清理不必要的文件

echo "=========================================="
echo "Claude 监控器 - 清理不必要的文件"
echo "=========================================="
echo ""

cd /mnt/SSD/opt/claude-monitor

# 创建 backup 目录
mkdir -p .archive

echo "正在归档旧文件..."

# 归档旧版本
for file in auto.py claude-auto.py claude-interactive.py claude-monitor.py claude-watcher.py; do
    if [ -f "$file" ]; then
        mv "$file" .archive/
        echo "  归档: $file"
    fi
done

# 归档旧脚本
for file in ccc.sh interactive.sh rcc.sh start.sh watch.sh; do
    if [ -f "$file" ]; then
        mv "$file" .archive/
        echo "  归档: $file"
    fi
done

# 归档临时文件
for file in debug-confirm.py realtime-monitor.py show_session.py check_claude.sh qwen_helper.py hybrid_confirmer.py pure_ai_confirmer.py; do
    if [ -f "$file" ]; then
        mv "$file" .archive/
        echo "  归档: $file"
    fi
done

# 归档临时文档
for file in FIXES.md PROBLEM_ANALYSIS.md QUICKSTART.md; do
    if [ -f "$file" ]; then
        mv "$file" .archive/
        echo "  归档: $file"
    fi
done

# 归档测试脚本（保留在 tests/ 中）
if [ -f "simple_confirm.py" ]; then
    mv simple_confirm.py .archive/
    echo "  归档: simple_confirm.py"
fi

echo ""
echo "=========================================="
echo "清理完成！"
echo "=========================================="
echo ""
echo "保留的主要文件:"
echo "  ✓ smart_confirmer.py        - 智能确认器（推荐）"
echo "  ✓ claude-auto-confirm.py    - 基础确认器（带历史）"
echo "  ✓ simple_rule_confirmer.py  - 简单规则确认器"
echo "  ✓ confirm_history.py        - 历史记录模块"
echo "  ✓ quick-start.sh            - 快速启动脚本"
echo "  ✓ README.md                 - 完整文档"
echo "  ✓ tests/                    - 测试程序"
echo ""
echo "归档的文件保存在: .archive/"
echo ""
