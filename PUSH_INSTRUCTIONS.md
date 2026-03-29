# Git 推送失败 - 需要身份验证

## 问题

推送失败，需要 GitHub 身份验证。

## 解决方案

### 方案 1: 使用 SSH 密钥（推荐）

```bash
# 1. 生成 SSH 密钥（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 查看公钥
cat ~/.ssh/id_ed25519.pub

# 3. 复制公钥到 GitHub
#    GitHub -> Settings -> SSH and GPG keys -> New SSH key

# 4. 修改远程地址为 SSH
cd /mnt/SSD/opt/claude-monitor
git remote set-url origin git@github.com:grigs28/claude-monitor.git

# 5. 推送
git push -u origin main
```

### 方案 2: 使用 Personal Access Token

```bash
# 1. 在 GitHub 创建 Token
#    GitHub -> Settings -> Developer settings -> Personal access tokens -> Generate new token
#    勾选 repo 权限

# 2. 使用 Token 推送
cd /mnt/SSD/opt/claude-monitor
git remote set-url origin https://YOUR_TOKEN@github.com/grigs28/claude-monitor.git
git push -u origin main
```

### 方案 3: 手动输入用户名密码

```bash
cd /mnt/SSD/opt/claude-monitor
GIT_TERMINAL_PROMPT=1 git push -u origin main
# 然后输入 GitHub 用户名和密码（或 Token）
```

### 方案 4: 使用 Git Credential Helper

```bash
# 配置 credential helper
git config --global credential.helper store

# 推送时会提示输入用户名密码（或 Token）
git push -u origin main
```

## 当前状态

✅ Git 仓库已初始化
✅ 所有文件已提交
✅ 主分支已重命名为 main
✅ 远程仓库已添加
❌ 推送需要身份验证

## 推荐步骤

1. **最简单**: 在本地终端手动执行推送命令
2. **最安全**: 使用 SSH 密钥
3. **最直接**: 使用 Personal Access Token

选择一个方案后，在终端执行相应的命令即可！
