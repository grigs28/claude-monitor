# Contributing to Claude Auto Confirmer

感谢你对 Claude Auto Confirmer 的贡献！

## 如何贡献

### 报告问题

如果你发现了 bug，请：
1. 检查 [Issues](../../issues) 是否已有相同问题
2. 如果没有，创建新 Issue，包含：
   - 问题描述
   - 复现步骤
   - 预期行为
   - 实际行为
   - 环境信息（OS, Python 版本等）

### 提交代码

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发指南

#### 代码风格
- 遵循 PEP 8 规范
- 添加适当的注释和文档字符串
- 保持函数简短、专注

#### 测试
- 为新功能添加测试
- 确保所有测试通过
- 在 `tests/` 目录添加测试脚本

#### 文档
- 更新相关文档
- 添加使用示例

## 开发环境设置

```bash
# 克隆仓库
git clone <your-fork-url>
cd claude-monitor

# 安装依赖（如果需要）
pip install -r requirements.txt

# 运行测试
cd tests
./simple_test.sh
```

## Pull Request 审查标准

- 代码清晰、易读
- 有适当的测试覆盖
- 文档已更新
- 通过所有现有测试
- 遵循代码风格

## 获取帮助

- 查看 [README.md](README.md)
- 查看 [文档](docs/)
- 提交 Issue

再次感谢你的贡献！
