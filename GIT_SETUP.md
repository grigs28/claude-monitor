# Claude Auto Confirmer - Git 提交准备

## 初始化仓库

```bash
cd /mnt/SSD/opt/claude-monitor
git init
```

## 添加文件

```bash
git add .
```

## 首次提交

```bash
git commit -m "Initial commit: Claude Auto Confirmer v1.0.0

Features:
- Smart confirmer with dual mode (rule-based and AI-powered)
- Rule-based fast confirmation
- AI-powered intelligent confirmation using Qwen 3.5
- Automatic prompt detection for Claude Code
- Priority selection for 'always allow' options
- Duplicate prevention
- Command line detection
- Confirmation history tracking

Files:
- smart_confirmer.py: Main confirmer with dual mode
- claude-auto-confirm.py: Basic confirmer with history
- simple_rule_confirmer.py: Simple rule-based confirmer
- confirm_history.py: History tracking module
- tests/: Test scripts and utilities
- README.md: Complete Chinese documentation
- README_EN_CN.md: Bilingual English/Chinese guide
- CHANGELOG.md: Version history
- CONTRIBUTING.md: Contribution guide
- LICENSE: MIT License
"
```

## 添加远程仓库（在获得地址后）

```bash
# 替换 YOUR_REPO_URL 为实际的仓库地址
git remote add origin YOUR_REPO_URL

# 或使用 SSH
git remote add origin git@github.com:USERNAME/REPO.git
```

## 推送到远程

```bash
git branch -M main
git push -u origin main
```

## 检查状态

```bash
# 查看状态
git status

# 查看日志
git log --oneline

# 查看远程
git remote -v
```

## 标签（可选）

```bash
git tag -a v1.0.0 -m "Version 1.0.0 - Initial release"
git push origin v1.0.0
```
