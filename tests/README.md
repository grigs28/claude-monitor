# Claude Auto Confirmer - 测试套件

## 测试脚本

### 主要测试

- **simple_test.sh** - 简化测试（推荐首先运行）
  - 模拟确认提示，不启动 Claude Code
  - 快速验证确认器功能
  
- **run_test.sh** - 完整测试
  - 启动真实的 Claude Code
  - 全面测试确认器功能

- **simulate_confirm.sh** - 交互式模拟
  - 手动选择测试场景
  - 在 tmux 会话中模拟各种提示

### Python 测试

- **test_claude_confirm.py** - Python 单元测试
  - 模式检测测试
  - tmux 集成测试

## 快速开始

```bash
# 1. 快速测试（推荐）
./simple_test.sh

# 2. 完整测试
./run_test.sh

# 3. 交互式模拟
./simulate_confirm.sh
```

## 测试说明

所有测试脚本都会：
1. 创建测试 tmux 会话
2. 模拟确认提示
3. 启动确认器
4. 验证自动确认
5. 清理测试会话

## 注意事项

⚠️ **警告**: 测试脚本会创建和销毁 tmux 会话
- 确保没有重要的 tmux 会话使用相同的名称
- 测试完成后会自动清理
- 如果测试中断，手动运行 `tmux kill-session -t <session-name>`
