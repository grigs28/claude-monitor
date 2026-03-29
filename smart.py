#!/usr/bin/env python3
"""
智能确认器 - 修复抓取范围
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

class SimpleConfirmer:
    def __init__(self, session_name="claude", use_ai=False):
        self.session_name = session_name
        self.use_ai = use_ai
        self.running = True
        self.confirm_count = 0
        self.ai_count = 0
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
            # 关键修复：增加抓取范围到800字符（原来是400）
            r = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p', '-J'],
                             capture_output=True, text=True, timeout=1)
            content = r.stdout
            # 取最后800字符，确保包含完整确认对话框
            if len(content) > 800:
                content = content[-800:]
            return content
        except:
            return ""
    
    def quick_check(self, text):
        """极简规则判断"""
        t = text.lower()
        
        # 调试打印（调试用，确认后注释掉）
        # print(f"DEBUG: do_you={'do you want' in t}, proceed={'proceed' in t}, 1.={'1.' in text}, ❯={'❯' in text}")
        
        # 认识的：看到 Do you want / proceed / requires approval + 有选项
        if (('do you want' in t or 'proceed' in t or 'requires approval' in t) and 
            ('1.' in text or '❯' in text)):
            # 有 always 选2
            if '2.' in text and ('always' in t or 'don\'t ask' in t):
                return True, "2", "rule:always"
            return True, "1", "rule:yes"
        
        return None, None, None
    
    def has_yes_no(self, text):
        """检测是否有 Yes/No 选项"""
        t = text.lower()
        
        # 标准选项
        if '1.' in text and ('yes' in t or 'no' in t):
            return True
        if '❯' in text and '1.' in text:
            return True
        if '[y/n]' in t or '(y/n)' in t:
            return True
        
        # 更宽松：看到 yes/no 单词就行
        if 'yes' in t and 'no' in t:
            return True
        
        return False
    
    def ask_ai(self, text):
        """AI判断"""
        self.ai_count += 1
        
        prompt = (
            "判断是否需要确认。屏幕：\n```\n" + text[-400:] + "\n```\n"
            "规则：\n"
            "1. 看到'Yes/No'选项，返回true选1\n"
            "2. 看到'always allow'选2\n"
            "3. 看到错误/删除，返回false\n"
            "4. 普通命令行，返回false\n\n"
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
                    "max_tokens": 60
                },
                timeout=self.timeout
            )
            
            if r.status_code == 200:
                result = r.json()
                content = result['choices'][0]['message']['content']
                confirm = 'true' in content.lower() and '"confirm":true' in content.replace(' ', '')
                action = "2" if '"action":"2"' in content or '"action": "2"' in content else "1"
                return confirm, action, "ai"
            return False, None, "api_error"
        except:
            return False, None, "exception"
    
    def send(self, key):
        try:
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, key], 
                          check=False, timeout=1)
            time.sleep(0.05)
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, 'Enter'], 
                          check=False, timeout=1)
            self.confirm_count += 1
            print(f"\n[确认] 发送 '{key}' (第{self.confirm_count}次)")
            return True
        except:
            return False
    
    def run(self):
        mode = "规则+AI兜底" if self.use_ai else "纯规则"
        print(f"极简确认器 ({mode}) 监控 {self.session_name}")
        print(f"[修复] 抓取范围扩大到800字符，确保看到完整确认对话框")
        print(f"冷却期{self.cooldown}秒，Ctrl+C停止")
        
        while self.running:
            if time.time() - self.last_confirm_time < self.cooldown:
                time.sleep(0.3)
                continue
            
            text = self.get_screen()
            if not text:
                time.sleep(1)
                continue
            
            # 第一步：规则判断
            should, action, reason = self.quick_check(text)
            
            # 第二步：规则不认识，AI兜底（如果开启）
            if should is None:
                if self.use_ai and self.has_yes_no(text):
                    should, action, reason = self.ask_ai(text)
                    if should:
                        print(f"[AI] 确认: {action}")
                    else:
                        print(f"[AI] 跳过")
                        time.sleep(1)
                        continue
                else:
                    time.sleep(1)
                    continue
            
            # 执行
            if should:
                if self.send(action):
                    self.last_confirm_time = time.time()
                    time.sleep(1)
                else:
                    time.sleep(0.5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--ai", action="store_true", help="AI兜底")
    args = parser.parse_args()
    
    c = SimpleConfirmer(args.session, use_ai=args.ai)
    try:
        c.run()
    except KeyboardInterrupt:
        extra = f" AI调用{c.ai_count}次" if c.use_ai else ""
        print(f"\n总计: 确认{c.confirm_count}次{extra}")