# 模型切换定时任务

## 🕐 高峰时段配置

**高峰时段**: 13:55 - 18:05（下午 2:55 PM - 6:05 PM）

## 📋 模型分配

| 时段 | Claude Code | 你（助手） |
|------|-----------|----------|
| **高峰** | glm-5.1 | glm-4.7 |
| **其他** | glm-4.7 | glm-turbo |

## ⏰ 定时任务

### 方式 1: crontab（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加以下行：

# 高峰时段整点检查（14:00, 15:00, 16:00, 17:00, 18:00）
0 14,15,16,17,18 * * * cd /mnt/SSD/opt/claude-monitor && /mnt/SSD/opt/claude-monitor/switch_model.sh >> /tmp/model-switch.log 2>&1

# 或每 5 分钟检查一次（13:55-18:05 时段）
*/5 13-18 * * * cd /mnt/SSD/opt/claude-monitor && /mnt/SSD/opt/claude-monitor/switch_model.sh >> /tmp/model-switch.log 2>&1
```

### 方式 2: systemd timer（精确控制）

```bash
cat > /etc/systemd/system/claude-model-switch.service << 'EOF'
[Unit]
Description=Claude 模型切换服务

[Service]
Type=oneshot
User=root
WorkingDirectory=/mnt/SSD/opt/claude-monitor
ExecStart=/mnt/SSD/opt/claude-monitor/switch_model.py

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/claude-model-switch.timer << 'EOF'
[Unit]
Description=定时检查并切换 Claude 模型
OnCalendar=Mon,Tue,Wed,Thu,Fri,Sat,Sun *-* 13:55,14:55,15:55,16:55,17:55,18:05

[Install]
WantedBy=timers.target
EOF

# 启用
systemctl daemon-reload
systemctl enable claude-model-switch.timer
systemctl start claude-model-switch.timer
```

## 🔧 当前时间判断逻辑

```python
import datetime

now = datetime.now()

# 高峰时段：13:55-18:05
is_peak = (now.hour == 13 and now.minute >= 55) or (14 <= now.hour < 18)

if is_peak:
    print("高峰时段: 使用 glm-4.7 (你) / glm-5.1 (Claude)")
else:
    print("非高峰: 使用 glm-turbo (你) / glm-4.7 (Claude)")
```

## 📊 模型配置

### API Keys

- **glm-4.7**: `sk-3b39IVbVp1iLmRHCZ58vLve5bmnyYIo6ntEvTyFbLWcSaJS7`
- **glm-turbo**: （需要添加）
- **glm-5.1**: （需要添加）
- **glm-4**: （需要添加）

## ⏰ 测试

```bash
# 测试时间判断逻辑
python3 /mnt/SSD/opt/claude-monitor/switch_model.py

# 查看日志
tail -f /tmp/model-switch.log
```

---

**推荐**: 使用 crontab 方式，简单直接！🕐
