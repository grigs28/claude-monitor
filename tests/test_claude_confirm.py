#!/usr/bin/env python3
"""
测试 Claude 自动确认器
模拟各种确认场景
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def create_test_session():
    """创建测试 tmux 会话"""
    session_name = "claude-test"
    
    # 检查会话是否存在
    result = subprocess.run(
        ['tmux', 'has-session', '-t', session_name],
        capture_output=True
    )
    
    if result.returncode == 0:
        print(f"[测试] 会话 '{session_name}' 已存在")
        return session_name
    
    # 创建新会话
    print(f"[测试] 创建 tmux 会话: {session_name}")
    subprocess.run([
        'tmux', 'new-session',
        '-d', '-s', session_name,
        '-n', 'test',
        'bash'
    ])
    
    # 等待会话启动
    time.sleep(1)
    
    return session_name

def cleanup_test_session(session_name: str):
    """清理测试会话"""
    print(f"[清理] 关闭测试会话: {session_name}")
    subprocess.run(['tmux', 'kill-session', '-t', session_name])

def test_pattern_detection():
    """测试模式检测"""
    print("\n" + "=" * 50)
    print("测试 1: 模式检测")
    print("=" * 50)
    
    test_cases = [
        ("编辑确认", "❯ 1. Yes / 2. Yes, allow all edits"),
        ("继续确认", "Do you want to proceed? (y/n)"),
        ("运行命令", "Run bash script? [Y/n]"),
        ("无确认", "Just some random text"),
    ]
    
    # 导入确认器
    from claude_confirm import ClaudeConfirmer
    
    confirmer = ClaudeConfirmer()
    confirmer.setup_patterns()
    
    for name, content in test_cases:
        result = confirmer.detect_confirm(content)
        if result:
            confirm_type, key = result
            print(f"  ✓ {name}: 检测到类型 '{confirm_type}', 按键 '{key}'")
        else:
            print(f"  ✗ {name}: 未检测到确认")

def test_tmux_integration():
    """测试 tmux 集成"""
    print("\n" + "=" * 50)
    print("测试 2: tmux 集成")
    print("=" * 50)
    
    session_name = create_test_session()
    
    try:
        # 导入确认器
        from claude_confirm import ClaudeConfirmer
        
        confirmer = ClaudeConfirmer(session_name)
        
        # 测试捕获
        print("\n[测试] 捕获 pane 内容...")
        content = confirmer.capture_pane()
        if content:
            print(f"  ✓ 成功捕获 {len(content)} 字符")
            print(f"  内容预览: {content[:100]}...")
        else:
            print(f"  ✗ 捕获失败")
        
        # 测试发送按键
        print("\n[测试] 发送测试按键...")
        result = confirmer.send_confirm("echo test")
        if result:
            print(f"  ✓ 按键发送成功")
        else:
            print(f"  ✗ 按键发送失败")
        
        # 等待并再次捕获
        time.sleep(0.5)
        content_after = confirmer.capture_pane()
        if content_after and "test" in content_after:
            print(f"  ✓ 按键生效检测成功")
        
    finally:
        cleanup_test_session(session_name)

def test_manual_scenario():
    """手动测试场景"""
    print("\n" + "=" * 50)
    print("测试 3: 手动测试场景")
    print("=" * 50)
    
    print("""
这个测试需要手动操作：

1. 在一个 tmux 会话中启动 Claude Code
2. 运行确认器监控该会话：
   python3 /mnt/SSD/opt/claude-monitor/claude-confirm.py <会话名>
3. 在 Claude Code 中触发需要确认的操作
4. 观察确认器是否自动检测并发送确认

示例：
  # 终端 1: 在 tmux 会话中运行 Claude
  tmux new-session -s claude
  conda activate taf
  cd /mnt/SSD/webapp/TAF
  claude
  
  # 终端 2: 运行确认器
  python3 /mnt/SSD/opt/claude-monitor/claude-confirm.py claude
  
  # 在 Claude 中请求编辑文件，观察确认器是否自动确认
    """)

def main():
    print("=" * 50)
    print("Claude 自动确认器测试")
    print("=" * 50)
    
    # 运行测试
    test_pattern_detection()
    test_tmux_integration()
    test_manual_scenario()
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
