# GitHub 推送身份验证指南

## 方法 1: 使用 Personal Access Token（推荐）

### 步骤 1: 创建 Personal Access Token

1. 打开浏览器，访问：https://github.com/settings/tokens
2. 点击 "Generate new token" (classic)
3. 设置：
   - **Note**: `claude-monitor-push`
   - **Expiration**: 选择过期时间（或 No expiration）
   - **Scopes**: 勾选 `repo` (full control of private repositories)
4. 点击 "Generate token"
5. **重要**: 复制生成的 token（只显示一次！）

### 步骤 2: 推送

在终端执行：
```bash
cd /mnt/SSD/opt/claude-monitor
git push -u origin main
```

当提示输入用户名和密码时：
- **Username**: `grigs28`
- **Password**: 粘贴刚才复制的 Personal Access Token

---

## 方法 2: 使用 GitHub CLI（最简单）

### 步骤 1: 安装 GitHub CLI

```bash
# CentOS/RHEL
sudo dnf install gh

# Ubuntu/Debian
sudo apt install gh

# 或使用 snap
sudo snap install gh
```

### 步骤 2: 登录

```bash
gh auth login
```

会打开浏览器，授权即可。

### 步骤 3: 推送

```bash
cd /mnt/SSD/opt/claude-monitor
git push -u origin main
```

---

## 方法 3: 配置 SSH 密钥（一劳永逸）

### 步骤 1: 生成 SSH 密钥

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# 一路回车即可
```

### 步骤 2: 查看公钥

```bash
cat ~/.ssh/id_ed25519.pub
```

### 步骤 3: 添加到 GitHub

1. 访问：https://github.com/settings/keys
2. 点击 "New SSH key"
3. Title: 填写 `claude-monitor`
4. Key: 粘贴公钥内容
5. 点击 "Add SSH key"

### 步骤 4: 测试并推送

```bash
# 测试连接
ssh -T git@github.com

# 推送
cd /mnt/SSD/opt/claude-monitor
git push -u origin main
```

---

## 推荐方案

**如果你经常推送** → 使用 SSH 密钥（方法 3）
**如果只是偶尔推送** → 使用 Personal Access Token（方法 1）
**如果想要最简单** → 使用 GitHub CLI（方法 2）

## 当前状态

✅ 代码已提交到本地
✅ 远程仓库已配置
⏳ 等待身份验证推送

选择一个方法，在终端执行相应的命令即可！
