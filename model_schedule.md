# 模型切换定时任务说明

## 时间段定义

| 时段 | 说明 | 使用模型 |
|------|------|---------|
| **高峰** | 13:55 - 18:05 | glm-4.7 |
| **其他时间** | 剩余时间 | glm-turbo |
| **Claude Code** | 高峰时用 glm-5.1 | 其他时间用 glm-4.7 |

## 定时任务配置

```bash
# 每小时的第 55 分检查一次（13:55, 14:55, 15:55, 16:55, 17:55）
55 13-18 * * * * cd /mnt/SSD/opt/claude-monitor && /mnt/SSD/opt/claude-monitor/switch_model.sh

# 或者在整点检查（14:00, 15:00, 16:00, 17:00, 18:00）
0 14,15,16,17,18 * * * cd /mnt/SSD/opt/claude-monitor && /mnt/SSD/opt/claude-monitor/switch_model.sh
```

## 待实现

需要实现的功能：
1. 修改 Claude Code 的模型配置文件
2. 切换 API key（4.7 vs 其他）
3. 模型切换通知

## 说明

**高峰时段**: 下午 1:55 PM - 6:05 PM（大家都用 Claude）
**非高峰**: 其他时间（资源充足，用 turbo）

这样可以避免高峰时段资源冲突！
