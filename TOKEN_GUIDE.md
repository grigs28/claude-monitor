# GitHub Token 类型选择

## ❌ 不要使用 Fine-grained tokens

**Fine-grained personal access tokens** 是新的功能，但有些工具可能还不兼容。

## ✅ 请使用 Personal access tokens (classic)

在页面顶部，你应该看到两个选项：

### 正确的路径：

1. 在当前页面顶部，点击：
   **"Personal access tokens (classic)"**

2. 点击右侧的：
   **"Generate new token"** (classic)

3. 配置：
   - **Note**: `claude-monitor-push`
   - **Expiration**: `90 days` 或 `No expiration`
   - **Scopes**: 只勾选 ✅ **repo** (Full control of private repositories)

4. 点击 **"Generate token"**

5. 复制生成的 token（只显示一次！）

## 对比

| 类型 | 状态 | 说明 |
|------|------|------|
| **Classic** | ✅ 使用 | 兼容性好，简单直接 |
| Fine-grained | ❌ 不用 | 新功能，可能不兼容 |

## 注意

- 必须点击 **"Personal access tokens (classic)"**
- 不是 "Fine-grained personal access tokens"

确认在正确的页面后再生成 token！
