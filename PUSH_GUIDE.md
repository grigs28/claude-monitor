# Git 推送指南

## 问题
自动推送失败，需要身份验证。

## 解决方案

### 方案 1: 使用 GitHub CLI（最简单）

```bash
# 安装 GitHub CLI（如果还没有）
# 在 Linux: 
#   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
#   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/githubcli.list
#   sudo apt update
#   sudo apt install gh

# 登录 GitHub
gh auth login

# 推送
cd /mnt/SSD/opt/claude-monitor
git push -u origin main
```

### 方案 2: 使用 Personal Access Token

```bash
cd /mnt/SSD/opt/claude-monitor

# 1. 在 GitHub 创建 Token:
#    https://github.com/settings/tokens/new
#    勾选: repo (full control)
#    生成并复制 Token

# 2. 使用 Token 推送
git remote set-url origin https://YOUR_TOKEN@github.com/grigs28/claude-monitor.git
git push -u origin main

# 3. 推送后恢复原始地址（可选）
git remote set-url origin https://github.com/grigs28/claude-monitor.git
```

### 方案 3: 配置 SSH 密钥

```bash
# 1. 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 查看公钥
cat ~/.ssh/id_ed25519.pub

# 3. 添加公钥到 GitHub
#    GitHub -> Settings -> SSH and GPG keys -> New SSH key
#    粘贴公钥内容

# 4. 测试连接
ssh -T git@github.com

# 5. 推送
cd /mnt/SSD/opt/claude-monitor
git push -u origin main
```

### 方案 4: 在本地终端手动推送

最简单的方法：
```bash
cd /mnt/SSD/opt/claude-monitor
git push -u origin main
```

然后输入 GitHub 用户名和密码/Token。

## 当前状态

✅ 所有文件已提交到本地 Git
✅ 远程仓库已配置
❌ 推送需要身份验证

## 推荐操作

**在本地终端执行**:
```bash
cd /mnt/SSD/opt/claude-monitor
git push -u origin main
```

然后按提示输入 GitHub 用户名和 Personal Access Token。

或者使用 GitHub CLI (`gh auth login` + `git push`)。
