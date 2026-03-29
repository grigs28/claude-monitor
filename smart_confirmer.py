#!/usr/bin/env python3
"""
智能确认器 - git push 修复版（紧急）
问题：可能没抓到完整屏幕，或冷却期阻止
"""

import subprocess
import requests
import time
import re
import sys
import argparse
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

class FixConfirmer:
    def __init__(self, session_name="claude", use_ai=False):
        self.session_name = session_name
        self.use_ai = use_ai
        self.running = True
        self.confirm_count = 0
        self.ai_count = 0
        # 关键修复：启动时重置冷却期，确保第一次能立即点
        self.last_confirm_time = 0  
        self.cooldown = 2
        
        if use_ai:
            env_path = Path(__file__).parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
            self.api_url = os.getenv('QWEN_API_URL', 'http://192.168.0.70:5564/v1/chat/completions')
            self.model = os.getenv('QWEN_MODEL', '/opt/models/Qwen/Qwen3.5-27B-FP8')
            self.timeout = int(os.getenv('QWEN_TIMEOUT', '30'))
    
    def get_screen(self):
        try:
            # 关键修复：抓1000字符，确保看到 "This command requires approval"
            r = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p', '-J'],
                             capture_output=True, text=True, timeout=1)
            content = r.stdout
            if len(content) > 1000:
                content = content[-1000:]
            return content
        except Exception as e:
            print(f"[错误] {e}")
            return ""
    
    def should_confirm(self, text):
        """
        统一判断逻辑（规则+AI）
        返回: (should, action, reason)
        """
        t = text.lower()
        
        # 调试：打印关键匹配（看实际抓到了什么）
        has_approval = 'requires approval' in t
        has_do_you = 'do you want' in t
        has_proceed = 'proceed' in t
        has_option1 = '1.' in text
        has_arrow = '❯' in text
        has_yes = 'yes' in t
        
        print(f"  [检测] approval={has_approval}, do_you={has_do_you}, proceed={has_proceed}, 1.={has_option1}, ❯={has_arrow}, yes={has_yes}")
        
        # 规则1：明确的确认提示（requires approval / Do you want / proceed）
        if (has_approval or has_do_you or has_proceed) and (has_option1 or has_arrow):
            # 有 always 选2，否则选1
            if '2.' in text and ('always' in t or 'don\'t ask' in t or '’t ask' in t):  # 处理智能引号
                return True, "2", "rule:always"
            return True, "1", "rule:yes"
        
        # 规则不认识，检查是否有 Yes/No（给AI用）
        has_options = has_option1 or has_arrow or ('yes' in t and 'no' in t)
        
        if self.use_ai and has_options:
            # AI兜底
            return self.ask_ai(text)
        
        # 不认识也没有Yes/No，跳过
        return False, None, "skip"
    
    def ask_ai(self, text):
        """AI判断"""
        self.ai_count += 1
        print("  → 调用AI...")
        
        prompt = (
            "判断是否需要确认。屏幕最后300字符：\n```\n" + text[-300:] + "\n```\n"
            "看到'Yes'选项就返回true选1，看到'always allow'选2，其他false。\n"
            "JSON: {\"confirm\":true/false,\"action\":\"1\"/\"2\"}"
        )
        
        try:
            r = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 50
                },
                timeout=self.timeout
            )
            
            if r.status_code == 200:
                result = r.json()
                content = result['choices'][0]['message']['content']
                confirm = 'true' in content.lower() and '"confirm":true' in content.replace(' ', '')
                action = "2" if '"action":"2"' in content else "1"
                print(f"  [AI结果] confirm={confirm}, action={action}")
                return confirm, action, "ai"
            else:
                print(f"  [AI错误] {r.status_code}")
                return False, None, "api_error"
        except Exception as e:
            print(f"  [AI异常] {e}")
            return False, None, "exception"
    
    def send(self, key):
        try:
            print(f"  → 发送按键 '{key}'...")
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, key], 
                          check=False, timeout=1)
            time.sleep(0.05)
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, 'Enter'], 
                          check=False, timeout=1)
            self.confirm_count += 1
            self.last_confirm_time = time.time()  # 记录确认时间
            print(f"\n>>> [成功] 第{self.confirm_count}次确认 <<<\n")
            return True
        except Exception as e:
            print(f"\n>>> [失败] {e} <<<\n")
            return False
    
    def run(self):
        mode = "规则+AI" if self.use_ai else "纯规则"
        print("=" * 70)
        print(f"紧急修复版 - 智能确认器 ({mode})")
        print(f"监控: {self.session_name} | 冷却期: {self.cooldown}秒")
        print("=" * 70)
        print("如果卡住，检查上面[检测]输出是否为True")
        print("=" * 70)
        
        check_num = 0
        while self.running:
            check_num += 1
            
            # 冷却期显示
            elapsed = time.time() - self.last_confirm_time
            if elapsed < self.cooldown:
                print(f"\r[检查{check_num}] 冷却中({self.cooldown-int(elapsed)}s)... ", end="")
                time.sleep(0.5)
                continue
            
            print(f"\n[检查{check_num}] 获取屏幕...")
            text = self.get_screen()
            
            if not text:
                print("  [空屏幕]")
                time.sleep(1)
                continue
            
            # 显示抓到的关键部分（看有没有 requires approval）
            preview = text[-200:].replace('\n', ' ')
            print(f"  [屏幕] ...{preview}")
            
            # 判断
            should, action, reason = self.should_confirm(text)
            
            if should:
                print(f"  [决策] 确认! 动作={action}, 原因={reason}")
                if self.send(action):
                    time.sleep(1.5)  # 确认后多等一会
                else:
                    time.sleep(0.5)
            else:
                print(f"  [决策] 跳过 ({reason})")
                time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--ai", action="store_true", help="AI兜底")
    args = parser.parse_args()
    
    c = FixConfirmer(args.session, use_ai=args.ai)
    try:
        c.run()
    except KeyboardInterrupt:
        print(f"\n\n总计: 确认{c.confirm_count}次" + (f", AI{c.ai_count}次" if c.use_ai else ""))