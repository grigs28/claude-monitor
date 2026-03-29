# Claude 自动确认器

自动监控并确认 Claude Code 的各种提示，让你的 AI 编程助手更加自动化。

## 🚀 快速开始

### 推荐方式（智能确认器）

```bash
# 规则模式（快速，默认）
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py claude

# AI 模式（智能判断）
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py claude --ai

# 监控指定会话
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py mysession
```

## ⚠️ AI 模式重要说明

### 💡 费用提醒

**强烈建议使用本地 AI 模型！**

| AI 模式 | 费用 | 说明 |
|--------|------|------|
| **本地模型** ✅ | **免费** | 推荐！无使用限制，响应快 |
| **在线 API** | 💰 **付费** | 按 token 计费，频繁调用会产生费用 |

### 本地模型配置（推荐）

```bash
# .env 文件配置
QWEN_API_URL=http://192.168.0.70:5564/v1/chat/completions
QWEN_MODEL=/opt/models/Qwen/Qwen/Qwen3.5-27B-FP8
```

**优势**:
- ✅ 完全免费
- ✅ 响应快速
- ✅ 保护隐私
- ✅ 无使用限制

### 在线 API 配置（需付费）

```bash
# .env 文件配置
MOONSHOT_API_KEY=your_api_key_here
MOONSHOT_API_URL=https://api.moonshot.cn/v1
MOONSHOT_MODEL=moonshot-v1-8k
```

**注意**:
- ⚠️ 按 token 计费
- ⚠️ 频繁调用会产生费用
- ⚠️ 建议仅在测试时使用
- ⚠️ 日常使用推荐本地模型

### 智能去重

AI 模式已优化：
- ✅ 内容相同时不重复调用 AI
- ✅ 只在屏幕内容变化时询问 AI
- ✅ 极大减少不必要的 AI 调用

## 📦 文件说明

```
claude-monitor/
├── smart_confirmer.py          # ⭐ 智能确认器（推荐）
├── claude-auto-confirm.py      # 基础确认器（带历史）
├── simple_rule_confirmer.py    # 简单规则确认器
├── confirm_history.py          # 历史记录模块
├── quick-start.sh              # 快速启动脚本
├── .env.example               # 配置模板
├── LICENSE                     # MIT 许可证
├── README.md                  # 完整文档
└── tests/                     # 测试程序
```

## 🎯 功能特性

### 两种模式对比

| 特性 | 规则模式 | AI 模式 |
|------|---------|---------|
| **速度** | ⚡ 快（1秒） | 🐢 慢（2秒+AI响应） |
| **准确度** | 🎯 高（简单规则） | 🧠 更高（AI理解） |
| **费用** | ✅ 免费 | 💰 需本地模型或付费 API |
| **依赖** | ✅ 无需外部 | ⚠️ 需要 AI 模型 API |
| **适用** | 日常使用 | 复杂场景 |

### 支持的确认类型

| 确认类型 | 示例文本 | 自动按键 |
|---------|---------|---------|
| 允许目录访问 | `Yes, allow reading from tmp/` | `2` |
| 永久允许访问 | `Yes, and always allow access` | `2` |
| 允许全部编辑 | `Yes, allow all edits` | `2` |
| 继续操作 | `Do you want to proceed?` | `1` |

### 智能特性

**规则模式**:
- ✅ 快速响应
- ✅ 优先选择 "always allow"
- ✅ 防频繁确认
- ✅ 自动跳过命令行

**AI 模式**:
- ✅ 智能理解
- ✅ 内容去重（相同内容不重复问 AI）
- ✅ 上下文感知
- ✅ 置信度评分

## 📝 使用场景

### 场景 1: 日常开发（推荐规则模式）

```bash
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py claude
```

### 场景 2: 复杂场景（使用 AI 智能判断）

```bash
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py claude --ai
```

## 🔧 配置

### 快速配置

```bash
# 1. 复制配置模板
cp /mnt/SSD/opt/claude-monitor/.env.example /mnt/SSD/opt/claude-monitor/.env

# 2. 编辑配置（使用本地模型）
nano /mnt/SSD/opt/claude-monitor/.env
```

### 配置说明

```bash
# .env 文件内容
QWEN_API_URL=http://192.168.0.70:5564/v1/chat/completions
QWEN_MODEL=/opt/models/Qwen/Qwen3.5-27B-FP8
```

**⚠️ 重要**:
- `.env` 文件不会被提交到 Git（已在 `.gitignore` 中）
- 保护你的 API 密钥和配置

## 🛡️ 安全注意事项

⚠️ **警告**:

1. **保护配置文件**
   - `.env` 包含敏感信息
   - 已在 `.gitignore` 中排除
   - 不要手动提交到 Git

2. **使用本地模型**
   - 推荐：免费、快速、隐私
   - 在线 API 会产生费用

3. **建议**
   - 优先使用规则模式（快速、可靠）
   - AI 模式仅在复杂场景使用
   - 定期检查 `.env` 配置

## 🔍 故障排除

### 问题: AI 模式不工作

**检查配置**:
```bash
# 检查 .env 文件
cat /mnt/SSD/opt/claude-monitor/.env

# 检查本地模型服务
curl http://192.168.0.70:5564/v1/models
```

**问题: 频繁调用 AI**

**解决方案**: 已优化
- AI 模式已添加内容去重
- 相同屏幕内容不会重复询问 AI
- 大幅减少不必要的调用

## 📊 版本兼容性

| Claude Code 版本 | 确认器版本 | 状态 |
|-----------------|-----------|------|
| 2.1.86 | 1.0+ | ✅ 完全支持 |

## 🤝 贡献

欢迎贡献！查看 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 许可

MIT License - 详见 [LICENSE](LICENSE)

---

**最后更新**: 2026-03-29
**版本**: 1.0
**Claude Code 版本**: 2.醒目 | Python | 3.7+
