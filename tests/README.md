# Claude 自动确认器 - 测试套件

这个目录包含完整的测试程序，用于验证 Claude Code 自动确认器的功能。

## 文件结构

```
/mnt/SSD/opt/claude-monitor/
├── claude-auto-confirm.py    # 主程序（自动确认器）
└── tests/
    ├── simple_test.sh          # 简化测试（模拟提示，不启动 Claude）
    ├── run_test.sh             # 完整测试（启动 Claude Code 并测试）
    ├── test_claude_confirm.py  # Python 单元测试
    └── README.md               # 本文件
```

## 快速测试

### 方法 1: 简化测试（推荐先试这个）

不需要启动 Claude Code，只模拟确认提示：

```bash
cd /mnt/SSD/opt/claude-monitor/tests
./simple_test.sh
```

**预期结果**:
- tmux 会话中显示确认提示
- 自动确认器检测到提示并发送按键 `1`
- 会话中出现 `1` 字符

### 方法 2: 完整测试

启动真实的 Claude Code 并测试自动确认：

```bash
cd /mnt/SSD/opt/claude-monitor/tests
./run_test.sh
```

**测试流程**:
1. 创建测试目录和文件
2. 启动 tmux 会话并运行 Claude Code
3. 启动自动确认器监控
4. 发送测试指令（要求编辑文件）
5. 观察确认器是否自动处理

### 方法 3: Python 单元测试

运行 Python 测试套件：

```bash
cd /mnt/SSD/opt/claude-monitor/tests
python3 test_claude_confirm.py
```

## 手动测试

### 步骤 1: 启动 Claude Code

```bash
tmux new-session -s claude
conda activate taf
cd /mnt/SSD/webapp/TAF
claude
```

### 步骤 2: 启动确认器

在另一个终端：

```bash
python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py claude
```

### 步骤 3: 触发确认

在 Claude Code 中执行需要确认的操作，比如：
- 请求编辑文件
- 运行命令
- 继续操作

### 步骤 4: 观察

确认器应该：
1. 检测到确认提示
2. 在终端输出检测信息
3. 自动发送确认按键

## 工作原理

```
┌─────────────────┐
│  tmux 会话      │
│  (Claude Code)  │
└────────┬────────┘
         │ 定期捕获
         ↓
┌─────────────────┐
│  自动确认器     │
│  - 检测提示     │
│  - 发送按键     │
└─────────────────┘
```

### 检测的提示类型

1. **编辑确认**: `Do you want to make this edit?`
2. **允许全部**: `Yes, allow all edits`
3. **继续操作**: `Do you want to proceed?`
4. **运行命令**: `Run bash script?`
5. **菜单选择**: `❯ 1. Option`

### 防重复机制

- 3 秒内不重复确认相同类型
- 内容哈希检查（5 秒内不重复相同内容）

## 配置

编辑 `/mnt/SSD/opt/claude-monitor/claude-auto-confirm.py`:

```python
DEFAULT_SESSION = "claude"      # 默认会话名
CHECK_INTERVAL = 0.5            # 检查间隔（秒）
CONFIRM_DELAY = 0.3             # 确认延迟（秒）
```

## 故障排除

### 问题: 确认器没有检测到提示

**可能原因**:
- 会话名不正确
- 提示文本格式不匹配
- 检查间隔太长

**解决方法**:
```bash
# 检查会话是否存在
tmux ls

# 查看会话内容
tmux capture-pane -t claude -p | tail -20

# 增加日志输出
# 在 claude-auto-confirm.py 中取消注释 print 语句
```

### 问题: 确认器重复确认

**解决方法**:
- 已有防重复机制（3秒）
- 如仍有问题，增加防重复时间

### 问题: 按键发送后没有生效

**解决方法**:
```python
# 增加确认延迟
CONFIRM_DELAY = 0.5  # 原来是 0.3
```

## 日志和调试

### 启用详细日志

修改 `claude-auto-confirm.py`，取消注释：

```python
print(f"[检测] 确认类型: {confirm_type}")
print(f"[内容预览] {content[-200:].strip()}")
```

### 查看实时输出

```bash
# 确认器输出会直接显示在终端
python3 claude-auto-confirm.py claude
```

## 实际使用

### 作为后台服务

```bash
# 启动确认器（后台运行）
nohup python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py claude > /tmp/claude-confirm.log 2>&1 &

# 查看日志
tail -f /tmp/claude-confirm.log

# 停止确认器
pkill -f "claude-auto-confirm.py"
```

### 与 cron 集成

```bash
# 添加到 crontab
# */5 * * * * /usr/bin/python3 /mnt/SSD/opt/claude-monitor/claude-auto-confirm.py claude >> /tmp/claude-confirm.log 2>&1
```

## 安全注意事项

⚠️ **警告**: 这个程序会自动确认 Claude Code 的提示

- 仅在测试环境使用
- 使用前备份重要文件
- 首次使用建议在 `simple_test.sh` 中验证
- 生产环境使用建议手动审查重要操作

## 清理

测试完成后：

```bash
# 关闭测试会话
tmux kill-session -t claude-test
tmux kill-session -t claude-simple-test

# 停止确认器
pkill -f "claude-auto-confirm.py"

# 清理测试文件
rm -rf /tmp/claude-test-*
```

## 贡献

如果发现新的确认模式，请修改 `claude-auto-confirm.py` 中的 `confirm_patterns` 列表。

## 反馈

测试有问题？请提供：
1. tmux 会话内容（`tmux capture-pane -t <session> -p`）
2. 确认器日志输出
3. Claude Code 版本信息
