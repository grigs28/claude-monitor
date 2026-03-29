#!/usr/bin/env python3
"""
智能确认器 - 支持规则和 AI 两种模式
支持 .env 配置文件
"""

import subprocess
import requests
import json
import time
import re
import sys
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

class SmartConfirmer:
    """智能确认器"""
    
    def __init__(self, session_name="claude", use_ai=False):
        self.session_name = session_name
        self.use_ai = use_ai
        
        # 加载 .env 配置
        self.load_env_config()
        
        # 运行状态
        self.running = True
        self.start_time = time.time()
        self.confirm_count = 0
        self.skip_count = 0
        self.last_confirm_time = 0
        
        # AI 模式：内容去重
        self.last_screen_hash = ""
        self.same_content_count = 0  # 记录相同内容次数
    
    def load_env_config(self):
        """加载环境变量配置"""
        # 加载 .env 文件
        env_path = Path(__file__).parent / '.env'
        load_dotenv(env_path)
        
        # AI 配置（从环境变量）
        self.api_url = os.getenv('QWEN_API_URL', 'http://192.168.0.70:5564/v1/chat/completions')
        self.model = os.getenv('QWEN_MODEL', '/opt/models/Qwen/Qwen3.5-27B-FP8')
        self.qwen_timeout = int(os.getenv('QWEN_TIMEOUT', '60'))
        
        # 通用配置
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '2'))
    
    def get_screen_content(self):
        """获取屏幕内容"""
        result = subprocess.run(
            ['tmux', 'capture-pane', '-t', self.session_name, '-p'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.stdout
    
    def rule_based_decision(self, content: str) -> tuple:
        """
        基于规则的判断
        返回: (should_confirm, action, reason)
        """
        now = time.time()
        
        # 防止频繁确认（至少间隔 3 秒）
        if now - self.last_confirm_time < 3:
            return (False, "", "距离上次确认不到 3 秒")
        
        # 检查是否在命令行
        if re.search(r'[\[\(][^\]\)]+[\]\)].*[\$#%]\s*$', content[-500:]):
            return (False, "", "在命令行中，跳过")
        
        # 检查确认提示
        has_prompt = False
        action = "1"
        
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
        
        if re.search(r'❯\s*\d+\.', content[-500:]) or re.search(r'\d+\.\s*Yes', content[-500:]):
            has_prompt = True
            
            if re.search(r'always allow|don.t ask again', content[-1000:], re.IGNORECASE):
                action = "2"
        
        if has_prompt:
            return (True, action, "规则检测到确认提示")
        
        return (False, "", "未检测到确认提示")
    
    def get_screen_hash(self, content: str) -> str:
        """生成屏幕内容哈希"""
        import hashlib
        # 只取最后 500 字符进行哈希
        return hashlib.md5(content[-500:].encode()).hexdigest()[:16]
    
    def is_page_static(self, content: str) -> bool:
        """检测页面是否静止（没有活动）"""
        # 检查是否在 Claude Code 的空闲状态
        idle_indicators = [
            r'❯\s*$',  # 只有光标，没有输入
            r'accept edits on.*shift\+tab',  # 提示信息
            r'⏵⏵ accept edits',  # 提示等待
        ]
        
        # 检查最后 300 字符
        recent = content[-300:]
        
        # 如果包含空闲指示符，认为页面静止
        for pattern in idle_indicators:
            if re.search(pattern, recent):
                return True
        
        return False
    
    def should_ask_ai(self, content: str) -> tuple:
        """
        判断是否应该询问 AI
        返回: (should_ask, reason)
        """
        # 生成当前屏幕哈希
        current_hash = self.get_screen_hash(content)
        
        # 如果内容和上次相同，不问 AI
        if current_hash == self.last_screen_hash:
            return (False, "内容未变化，跳过 AI 询问")
        
        # 内容变化，更新记录并询问 AI
        self.last_screen_hash = current_hash
        
        return (True, "内容已变化，询问 AI")
    
    def ai_based_decision(self, content: str) -> tuple:
        """
        基于 AI 的判断
        返回: (should_confirm, action, reason)
        """
        prompt = f"""你是 Claude Code 的自动确认助手。请分析屏幕内容并决定是否需要确认。

屏幕内容（最后 1500 字符）：
```
{content[-1500:]}
```

请判断并返回 JSON：
{{
    "is_confirm_prompt": true/false,
    "should_confirm": true/false,
    "action": "1"/"2"/"3"/"no",
    "reason": "简短原因说明",
    "confidence": 0.0-1.0
}}

注意：
- 只对 Claude Code 的确认提示进行确认
- 如果在命令行或有错误，不要确认
- 如果提示"always allow"或"don't ask again"，优先选择这些选项
"""
        
        try:
            headers = {"Content-Type": "application/json"}
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=self.qwen_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                parsed = json.loads(content)
                
                is_prompt = parsed.get("is_confirm_prompt", False)
                should = parsed.get("should_confirm", False)
                action = parsed.get("action", "1")
                reason = parsed.get("reason", "")
                confidence = parsed.get("confidence", 0)
                
                if is_prompt and should:
                    return (True, action, f"AI判断: {reason} (置信度: {confidence:.1%})")
                else:
                    return (False, "", f"AI判断: 不需要确认 - {reason}")
            else:
                return (False, "", f"AI错误: {response.status_code}")
        
        except Exception as e:
            return (False, "", f"AI请求失败: {str(e)[:50]}")
    
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
        mode = "AI模式" if self.use_ai else "规则模式"
        
        print("=" * 60)
        print(f"智能确认器 ({mode})")
        print("=" * 60)
        print(f"[会话] {self.session_name}")
        if self.use_ai:
            print(f"[模型] {self.model}")
            print(f"[API] {self.api_url}")
        else:
            print("[信息] 使用规则匹配，快速响应")
        print("[信息] 按 Ctrl+C 停止")
        print("=" * 60)
        print()
        
        check_interval = self.check_interval if self.use_ai else 1
        count = 0
        
        try:
            while self.running:
                count += 1
                
                # 每 30 次检查输出状态
                if count % 30 == 0:
                    elapsed = int(time.time() - self.start_time)
                    skip_info = f" | 跳过 {self.same_content_count} 次" if self.same_content_count > 0 else ""
                    print(f"[状态] 运行 {elapsed} 秒 | 确认 {self.confirm_count} 次{skip_info} | 内容未变化 哈哈🦐", flush=True)
                
                # 获取屏幕内容
                content = self.get_screen_content()
                
                if not content:
                    time.sleep(check_interval)
                    continue
                
                # 判断是否确认
                if self.use_ai:
                    # 先检查是否需要问 AI
                    should_ask_ai, skip_reason = self.should_ask_ai(content)
                    
                    if should_ask_ai:
                        should_confirm, action, ai_reason = self.ai_based_decision(content)
                        combined_reason = f"{ai_reason} ({skip_reason})"
                    else:
                        should_confirm, action, combined_reason = (False, "", skip_reason)
                        self.same_content_count += 1
                else:
                    should_confirm, action, combined_reason = self.rule_based_decision(content)
                
                if should_confirm:
                    print(f"\n[检测] {combined_reason}")
                    print(f"[执行] 发送按键: {action} + Enter")
                    
                    self.confirm(action)
                    
                    # 等待避免重复
                    time.sleep(3)
                else:
                    if combined_reason:  # 只在有原因时计数
                        self.skip_count += 1
                
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print("停止监控")
            print("=" * 60)
            elapsed = int(time.time() - self.start_time)
            print(f"运行时长: {elapsed} 秒")
            print(f"确认次数: {self.confirm_count}")
            print(f"跳过次数: {self.skip_count}")
            print(f"模式: {mode}")
            print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="智能确认器")
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--ai", action="store_true", help="使用 AI 模式（默认：规则模式）")
    parser.add_argument("--rule", action="store_true", help="使用规则模式")
    
    args = parser.parse_args()
    
    # 默认使用规则模式
    use_ai = args.ai
    
    confirmer = SmartConfirmer(args.session, use_ai)
    confirmer.monitor_loop()

if __name__ == "__main__":
    main()
