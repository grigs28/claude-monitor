# 模型配置和定时任务设置指南

## 🎯 时间段定义

| 时段 | 时间 | 说明 | Claude | 你（助手） |
|------|------|------|-------|----------|
| **高峰** | 13:55-18:05 | glm-5.1 | glm-4.7 |
| **其他时间** | 剩余时间 | glm-4.7 | glm-turbo |

## ⚙️ 创建定时任务

### 方法 1: crontab 格式

```bash
# 编辑 crontab
crontab -e

# 在高峰时段每小时检查一次（整点: 14:00, 15:00, 16:00, 17:00, 18:00）
0 14,15,16,17,18 * * * cd /mnt/SSD/opt/claude-monitor && /mnt/SSD/opt/claude-monitor/switch_model.sh

# 或每 5 分钟检查一次（覆盖式）
*/5 * 13-18 * * * cd /mnt/SD/opt/claude-monitor && /mnt/SSD/opt/claude-monitor/switch_model.sh

# 保存并退出
:wq
```

### 方法 2: systemd timer

```bash
# 创建 systemd timer 服务
cat > /etc/systemd/system/claude-model-switch.service << 'EOF'
[Unit]
Description=Claude 模型切换服务

[Service]
Type=oneshot
User=root
WorkingDirectory=/mnt/SSD/opt/claude-monitor
ExecStart=/mnt/SSD/opt/claude-monitor/switch_model.sh

[Install]
WantedBy=multi-user.target
EOF

# 创建 timer
cat > /etc/systemd/system/claude-model-switch.timer << 'EOF'
[Unit]
Description=定时检查并切换 Claude 模型
OnCalendar=Mon,Tue,Wed,Thu,Fri,Sat,Sun *-* 13:55,14:55,15:55,16:55,17:55,18:05

[Install]
WantedBy=timers.target
EOF

# 启用服务
systemctl daemon-reload
systemctl enable claude-model-switch.timer
systemctl start claude-model-switch.timer
```

## 🔧 切换逻辑

### 当前时间判断

```python3
import datetime

now = datetime.now()

# 高峰时段：13:55-18:05
if (now.hour == 13 and now.minute >= 55) or (14 <= now.hour < 18):
    model = "glm-4.7"          # 高峰用 4.7
else:
    model = "glm-turbo"         # 其他时间用 turbo
```

### API Key 配置

**Moonshot API Keys**:
- 4.7 API Key: `sk-3b39IVbVp1iLmRHCZ58vLve5bmnyYIo6ntEvTyFbLWcSaJS7`
- 其他模型 key: 对应的 API key

### 模型对应

| 模型 | API Key | 时段 |
|------|---------|------|
| **glm-4.7** | `sk-3b39IVbVp1iLmRHCZ58vLve5bmnyYIo6ntEvTyFbLWcSaJS7` | 高峰 + Claude |
| **glm-turbo** | （需要添加） | 非高峰 |
| **glm-5.1** | （需要添加） | 高峰 Claude |
| **glm-4** | （需要添加） | 非高峰 |

## 📋 创建定时任务

让我创建定时任务：
