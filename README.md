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

### 基础方式（带历史记录）

```bash
# 监控名为 'claude' 的 tmux 会话
python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py

# 后台运行
nohup python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py claude > /tmp/claude-confirm.log 2>&1 &
```

### 测试

```bash
# 简化测试（模拟提示，不启动 Claude）
cd /mnt/SSD/opt/claude-monitor/tests
./simple_test.sh

# 完整测试（启动真实 Claude Code）
./run_test.sh
```

## 📦 文件说明

```
claude-monitor/
├── smart_confirmer.py          # ⭐ 智能确认器（推荐，支持规则和AI两种模式）
├── claude-auto-confirm.py      # 基础确认器（带历史记录）
├── simple_rule_confirmer.py    # 简单规则确认器（快速）
├── pure_ai_confirmer.py        # 纯 AI 确认器（使用 Qwen）
├── confirm_history.py          # 确认历史管理模块
├── auto.py                     # 旧版本（pexpect 实现）
├── claude-auto.py              # 旧版本（PTY 实现）
├── claude-interactive.py       # 旧版本（交互模式）
├── claude-monitor.py           # 旧版本（监控器）
├── claude-watcher.py           # 旧版本（观察器）
├── quick-start.sh              # 快速启动脚本
└── tests/
    ├── simple_test.sh           # 简化测试
    ├── run_test.sh              # 完整测试
    ├── test_claude_confirm.py   # Python 单元测试
    ├── simulate_confirm.sh      # 模拟提示脚本
    └── README.md                # 测试说明
```

## 🎯 功能特性

### 两种模式对比

| 特性 | 规则模式 | AI 模式 |
|------|---------|---------|
| **速度** | ⚡ 快（1秒） | 🐢 慢（2秒+AI响应） |
| **准确度** | 🎯 高（简单规则） | 🧠 更高（AI理解） |
| **依赖** | ✅ 无需外部 | ⚠️ 需要 Qwen API |
| **网络** | ✅ 离线 | 🌐 需要本地网络 |
| **资源** | 💚 低 CPU | 🟡 中等 CPU |
| **适用** | 日常使用 | 复杂场景 |

### 支持的确认类型

| 确认类型 | 示例文本 | 自动按键 | 优先级 |
|---------|---------|---------|--------|
| 允许目录访问 | `Yes, allow reading from tmp/ during this session` | `2` | ⭐⭐⭐⭐⭐ |
| 永久允许访问 | `Yes, and always allow access to ... from this project` | `2` | ⭐⭐⭐⭐⭐ |
| 允许全部编辑 | `Yes, allow all edits for this session` | `2` | ⭐⭐⭐⭐ |
| 继续操作 | `Do you want to proceed?` | `1` | ⭐⭐⭐ |
| 运行命令 | `Run bash script?` | `1` | ⭐⭐ |
| 通用确认 | `❯ 1. Yes` | `1` | ⭐ |

### 智能特性

**规则模式**:
- ✅ **快速响应**: 1秒检查间隔
- ✅ **优先级系统**: 优先选择 "always allow" 选项
- ✅ **防频繁确认**: 3秒内不重复
- ✅ **命令行检测**: 自动跳过 bash 提示符

**AI 模式**:
- ✅ **智能理解**: 使用 Qwen 3.5 27B 分析
- ✅ **上下文感知**: 理解复杂场景
- ✅ **置信度评分**: 显示判断的置信度
- ✅ **详细原因**: AI 解释判断理由
- ✅ **超时控制**: 60秒超时，避免长时间等待

## 🔧 配置

### 智能确认器配置

```bash
# 规则模式（默认）
python3 smart_confirmer.py claude

# AI 模式
python3 smart_confirmer.py claude --ai

# 切换会话
python3 smart_confirmer.py mysession --ai
```

### AI 模型配置

编辑 `smart_confirmer.py` 中的配置：

```python
# 本地 Qwen 配置
self.api_url = "http://192.168.0.70:5564/v1/chat/completions"
self.model = "/opt/models/Qwen/Qwen3.5-27B-FP8"
```

### 基础确认器配置

编辑 `claude-auto-confirm.py` 中的配置常量：

```python
DEFAULT_SESSION = "claude"      # 默认监控的会话名
CHECK_INTERVAL = 0.3            # 检查间隔（秒）
CONFIRM_DELAY = 0.2             # 确认延迟（秒）
SESSION_TIMEOUT = 0             # 会话超时（0=永不超时）
```

## 📝 使用场景

### 场景 1: 日常开发（推荐规则模式）

```bash
# 启动规则模式确认器
python3 /mnt/SSD/opt/claude-monitor/smart_confirmer.py claude

# 在 Claude Code 中工作
# 所有确认自动处理，优先选择 "always allow"
```

```bash
# 终端 1: 启动 Claude Code
tmux new-session -s claude
conda activate taf
cd /mnt/SSD/webapp/TAF
claude

# 终端 2: 启动自动确认器
python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py claude

# 现在可以让 Claude 自动编辑文件、运行命令，无需手动确认
```

### 场景 2: 批量操作

```bash
# 启动确认器后台运行
nohup python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py claude > /tmp/claude-confirm.log 2>&1 &

# 让 Claude Code 批量处理多个文件
# 所有确认都会自动处理
```

### 场景 3: 测试环境

```bash
# 在测试环境中使用，让 Claude 自动运行测试、修复代码
# 无需手动点击确认
```

## 🛡️ 安全注意事项

⚠️ **警告**: 这个程序会自动确认 Claude Code 的提示

### 使用前必读

1. **仅在受信任的环境中使用**
   - 测试环境可以放心使用
   - 生产环境建议先审查重要操作

2. **备份重要文件**
   - 使用前备份重要代码
   - 确认器会自动允许文件编辑

3. **首次使用建议**
   - 先在 `simple_test.sh` 中验证
   - 观察确认器是否正确识别提示
   - 确认后再用于实际工作

4. **日志监控**
   - 后台运行时查看日志：`tail -f /tmp/claude-confirm.log`
   - 确保确认器正常工作

### 最佳实践

```bash
# 1. 启动时查看日志
python3 claude-auto-confirm.py claude | tee /tmp/claude-confirm.log

# 2. 定期检查日志
tail -f /tmp/claude-confirm.log

# 3. 完成后停止确认器
pkill -f "claude-auto-confirm.py"
```

## 🔍 故障排除

### 问题: 确认器没有检测到提示

**可能原因**:
- tmux 会话名不正确
- Claude Code 版本不匹配
- 提示文本格式变化

**解决方法**:
```bash
# 1. 检查会话是否存在
tmux ls

# 2. 查看会话内容
tmux capture-pane -t claude -p | tail -20

# 3. 检查 Claude 版本
claude --version

# 4. 查看确认器日志（如果有的话）
cat /tmp/claude-confirm.log
```

### 问题: 确认器重复确认

**说明**: 这是正常的，程序有防重复机制（3秒）

**如果仍有问题**:
```python
# 增加防重复时间（在 claude-auto-confirm.py 中）
if now - self.last_confirmed[confirm_type] < 5:  # 改为 5 秒
```

### 问题: 按键发送后没有生效

**解决方法**:
```python
# 增加确认延迟
CONFIRM_DELAY = 0.5  # 原来是 0.2
```

### 问题: 找不到 tmux 会话

**解决方法**:
```bash
# 创建 tmux 会话
tmux new-session -s claude

# 或者在确认器中指定正确的会话名
python3 claude-auto-confirm.py your-session-name
```

## 📊 版本兼容性

| Claude Code 版本 | 确认器版本 | 状态 |
|-----------------|-----------|------|
| 2.1.86 | 1.0+ | ✅ 完全支持 |
| 2.0.x | 1.0+ | ⚠️ 可能需要调整模式 |
| 1.x | 旧版本脚本 | ❌ 不支持 |

### 更新确认器

```bash
# 检查当前版本
head -5 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py

# 更新 Claude Code
conda update claude-code

# 验证兼容性
cd /mnt/SSD/opt/claude-monitor/tests
./simple_test.sh
```

## 🧪 测试

### 快速测试

```bash
cd /mnt/SSD/opt/claude-monitor/tests

# 简化测试（推荐）
./simple_test.sh

# 完整测试
./run_test.sh

# Python 单元测试
python3 test_claude_confirm.py
```

### 手动测试

```bash
# 1. 创建测试会话
tmux new-session -s test

# 2. 显示模拟提示
tmux send-keys -t test 'echo "Do you want to proceed?
>  ❯ 1. Yes
>    2. Yes, allow all
>    3. No"' Enter

# 3. 启动确认器
python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py test

# 4. 观察是否自动发送 '1'
```

## 📚 相关文档

- [测试文档](tests/README.md) - 详细的测试说明
- [Claude Code 官方文档](https://docs.anthropic.com/claude/docs/claude-code)
- [tmux 官方文档](https://github.com/tmux/tmux/wiki)

## 🤝 贡献

如果发现新的确认模式或有问题，欢迎反馈：

1. 记录确认提示的完整文本
2. 提供 Claude Code 版本信息
3. 提供确认器日志输出
4. 提交 issue 或 PR

## 📄 许可

本项目仅供个人学习和测试使用。

## 🎉 致谢

感谢 Claude Code 团队提供的优秀 AI 编程助手！

---

**最后更新**: 2026-03-29
**版本**: 1.0
**Claude Code 版本**: 2.1.86
