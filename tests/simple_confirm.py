#!/usr/bin/env python3
"""
超简化确认器 - 直接检测并发送
"""
import subprocess
import time

SESSION = "claude-test-improved"

print("=" * 50)
print("超简化确认器测试")
print("=" * 50)
print()

for i in range(20):
    # 捕获内容
    result = subprocess.run(
        ['tmux', 'capture-pane', '-t', SESSION, '-p'],
        capture_output=True,
        text=True
    )
    content = result.stdout
    
    # 简单检测：只要有 "Do you want to proceed" 和 "1. Yes"
    if "Do you want to proceed" in content and "1. Yes" in content:
        print(f"[{i+1}] 检测到确认提示！")
        
        # 发送按键 2 + Enter
        subprocess.run(['tmux', 'send-keys', '-t', SESSION, '2'])
        time.sleep(0.1)
        subprocess.run(['tmux', 'send-keys', '-t', SESSION, 'Enter'])
        
        print(f"[{i+1}] 已发送: 2 + Enter")
        
        # 等待并检查结果
        time.sleep(1)
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', SESSION, '-p'],
            capture_output=True,
            text=True
        )
        print("\n发送后的内容：")
        print(result.stdout[-500:])
        break
    else:
        if i % 5 == 0:
            print(f"[{i+1}] 等待确认提示...")
    
    time.sleep(0.5)

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
