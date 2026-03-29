#!/usr/bin/env python3
"""
模型切换脚本
根据当前时间自动选择合适的模型
"""

import os
import subprocess
import json
from datetime import datetime

def get_current_model():
    """根据时间返回应该使用的模型"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    
    # 高峰时段：13:55-18:05
    is_peak = (hour == 13 and minute >= 55) or (14 <= hour < 18)
    
    if is_peak:
        return {
            "model": "glm-4.7",
            "reason": "高峰时段",
            "claude_model": "glm-4.7",
            "your_model": "glm-4.7"
        }
    else:
        return {
            "model": "glm-turbo",
            "reason": "非高峰",
            "claude_model": "glm-5.1",
            "your_model": "glm-turbo"
        }

def switch_model():
    """切换到合适的模型"""
    config = get_current_model()
    
    print(f"\n{'='*60}")
    print(f"模型切换")
    print(f"{'='*60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"时段: {config['reason']}")
    print(f"模型: {config['model']}")
    print(f"Claude 建议: {config['claude_model']}")
    print(f"你建议: {config['your_model']}")
    print(f"{'='*60}")
    print()
    
    # 这里添加实际的切换逻辑
    # TODO: 调用 API 或修改配置文件
    
    return config

if __name__ == "__main__":
    config = switch_model()
    
    print("\n[状态] 模型需要手动切换")
    print("请根据上表选择合适的模型")
    print(f"\n推荐模型: {config['claude_model']}")
    print(f"推荐 API Key: 4.7 的 key")
