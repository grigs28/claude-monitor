#!/usr/bin/env python3
"""
简单规则确认器 - 不使用 AI，只用简单规则
"""

import subprocess
import time
import re
import sys

class SimpleRuleConfirmer:
    """简单规则确认器"""
    
    def __init__(self, session_name="claude"):
        self.session_name = session_name
        self.running = True
        self.start_time = time.time()
        self.confirm_count = 0
        self.last_confirm_time = 0
    
    def get_screen_content(self):
        """获取屏幕内容"""
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', self.session_name, '-p'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.stdout
    
    def should_confirm(self, content: str) -> tuple:
        """
        使用简单规则判断是否应该确认
        返回: (should_confirm, action, reason)
        """
        now = time.time()
        
        # 防止频繁确认（至少间隔 5 秒）
        if now - self.last_confirm_time < 5:
            return (False, "", "距离上次确认不到 5 秒")
        
        # 规则 1: 检查是否在命令行（有 bash 提示符）
        if re.search(r'[\[\(][^\]\)]+[\]\)].*[\$#%]\s*$', content[-500:]):
            return (False, "", "在命令行中，跳过")
        
        # 规则 2: 检查是否有确认提示
        has_prompt = False
        action = "1"
        
        # 检查确认问题
        confirm_keywords = [
            r'Do you want to proceed',
            r'always allow',
            r'allow all edits',
            r'don.t ask again'
        ]
        
        for keyword in confirm_keywords:
            if re.search(keyword, content[-1000:], re.IGNORECASE):
                has_prompt = True
                break
        
        # 检查选项
        if re.search(r'❯\s*\d+\.', content[-500:]) or re.search(r'\d+\.\s*Yes', content[-500:]):
            has_prompt = True
            
            # 检查是否有 "always allow" 选项
            if re.search(r'always allow|don.t ask again', content[-1000:], re.IGNORECASE):
                action = "2"  # 优先选择 "always allow"
        
        if has_prompt:
            return (True, action, "检测到确认提示")
        
        return (False, "", "未检测到确认提示")
    
    def confirm(self, action: str):
        """执行确认"""
        subprocess.run(['tmux', 'send-keys', '-t', self.session_name, action], 
                     check=False)
        time.sleep(0.1)
        subprocess.run(['tmux', 'send-keys', '-t', self.session_name, 'Enter'], 
                     check=False)
        self.last_confirm_time = time.time()
        self.confirm_count += 1
    
    def monitor_loop(self):
        """监控循环"""
        print("=" * 60)
        print("简单规则确认器")
        print("=" * 60)
        print(f"[会话] {self.session_name}")
        print("[信息] 使用简单规则匹配，不依赖 AI")
        print("[信息] 按 Ctrl+C 停止")
        print("=" * 60)
        print()
        
        check_interval = 1  # 每 1 秒检查一次
        count = 0
        
        try:
            while self.running:
                count += 1
                
                # 每 30 次检查输出状态
                if count % 30 == 0:
                    elapsed = int(time.time() - self.start_time)
                    print(f"[状态] 运行 {elapsed} 秒 | 确认 {self.confirm_count} 次", flush=True)
                
                # 获取屏幕内容
                content = self.get_screen_content()
                
                if not content:
                    time.sleep(check_interval)
                    continue
                
                # 判断是否确认
                should_confirm, action, reason = self.should_confirm(content)
                
                if should_confirm:
                    print(f"\n[检测] {reason}")
                    print(f"[执行] 发送按键: {action} + Enter")
                    
                    self.confirm(action)
                    
                    # 等待 3 秒避免重复
                    time.sleep(3)
                
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print("停止监控")
            print("=" * 60)
            elapsed = int(time.time() - self.start_time)
            print(f"运行时长: {elapsed} 秒")
            print(f"确认次数: {self.confirm_count}")
            print("=" * 60)

def main():
    session_name = sys.argv[1] if len(sys.argv) > 1 else "claude"
    
    confirmer = SimpleRuleConfirmer(session_name)
    confirmer.monitor_loop()

if __name__ == "__main__":
    main()
