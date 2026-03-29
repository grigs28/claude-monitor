#!/bin/bash
# 清理不必要的文件

echo "=========================================="
echo "清理不必要的文件"
echo "=========================================="
echo ""

cd /mnt/SSD/opt/claude-monitor

# 1. 删除重复的文档文件
echo "[1] 删除重复的文档..."
if [ -f "README_SHORT.md" ]; then
    rm README_SHORT.md
    echo "  删除: README_SHORT.md (已被 README.md 包含)"
fi

if [ -f "README_EN_CN.md" ]; then
    rm README_EN_CN.md
    echo "  删除: README_EN_CN.md (已被 README.md 包含)"
fi

if [ -f "GIT_SETUP.md" ]; then
    rm GIT_SETUP.md
    echo "  删除: GIT_SETUP.md (临时设置文件)"
fi

# 2. 删除临时脚本
echo "[2] 删除临时脚本..."
if [ -f "cleanup.sh" ]; then
    rm cleanup.sh
    echo "  删除: cleanup.sh (一次性清理脚本)"
fi

# 3. 保留主要文件，删除其他
echo "[3] 检查主要文件..."
main_files=(
    "smart_confirmer.py"
    "claude-auto-confirm.py"
    "simple_rule_confirmer.py"
    "confirm_history.py"
    "quick-start.sh"
    ".env.example"
    ".gitignore"
    "LICENSE"
    "README.md"
    "CHANGELOG.md"
    "CONTRIBUTING.md"
)

echo ""
echo "=========================================="
echo "保留的主要文件:"
echo "=========================================="
for file in "${main_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    fi
done

echo ""
echo "保留的目录:"
echo "  ✓ tests/          # 测试程序"
echo "  ✓ .archive/       # 归档文件"
echo "  ✓ .git/           # Git 仓库"
echo ""
echo "=========================================="
echo "清理完成！"
echo "=========================================="
