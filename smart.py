#!/usr/bin/env python3
"""
智能确认器 - 修复AI/规则判断逻辑
关键修复：
1. 规则对标准确认（Yes/No）直接选1，不发AI
2. AI Prompt 明确指示：看到"Do you want to"必须确认
3. 添加调试输出，可追踪判断过程
"""

import subprocess
import requests
import json
import time
import re
import sys
import argparse
import os
import hashlib
from pathlib import Path
from collections import deque

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass


class SmartConfirmer:
    def __init__(self, session_name="claude", use_ai=False, debug=False):
        self.session_name = session_name
        self.use_ai = use_ai
        self.debug = debug
        
        self.load_env_config()
        
        # 统计
        self.running = True
        self.start_time = time.time()
        self.confirm_count = 0
        self.suppress_count = 0
        self.skip_count = 0
        self.ai_call_count = 0
        self.rule_direct_count = 0
        
        # 控制
        self.last_confirm_time = 0
        self.cooldown_seconds = 5
        self.is_processing = False
        
        # 重复检测
        self.processed_prompts = deque(maxlen=20)
        
        # 间隔
        self.check_interval = 2.0
        self.cooldown_interval = 0.5
    
    def load_env_config(self):
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        self.api_url = os.getenv('QWEN_API_URL', 'http://192.168.0.70:5564/v1/chat/completions')
        self.model = os.getenv('QWEN_MODEL', '/opt/models/Qwen/Qwen3.5-27B-FP8')
        self.qwen_timeout = int(os.getenv('QWEN_TIMEOUT', '30'))
    
    def get_screen_content(self):
        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', self.session_name, '-p', '-J'],
                capture_output=True,
                text=True,
                timeout=2,
                check=True
            )
            content = result.stdout
            if len(content) > 2000:
                content = content[-2000:]
            return content
        except subprocess.CalledProcessError:
            print(f"\n[错误] tmux 会话 '{self.session_name}' 不存在")
            self.running = False
            return ""
        except FileNotFoundError:
            print("\n[错误] 未安装 tmux")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            return ""
    
    def compute_prompt_fingerprint(self, content):
        tail = content[-800:]
        lines = tail.split('\n')
        key_lines = []
        for line in lines:
            if re.search(r'[❯>\]]\s*\d+|\d+\.\s+(Yes|No|Always)', line, re.I):
                key_lines.append(line.strip()[:50])
        if len(key_lines) < 1:
            return None
        return hashlib.md5('|'.join(key_lines[-2:]).encode()).hexdigest()[:12]
    
    def is_in_cooldown(self):
        return (time.time() - self.last_confirm_time) < self.cooldown_seconds
    
    def is_prompt_processed(self, fingerprint):
        if fingerprint is None:
            return False
        now = time.time()
        for stored_fp, ts in self.processed_prompts:
            if stored_fp == fingerprint and (now - ts) < 300:
                return True
        return False
    
    def mark_prompt_processed(self, fingerprint):
        if fingerprint:
            self.processed_prompts.append((fingerprint, time.time()))
    
    def has_confirm_menu(self, content):
        """检测是否有确认菜单（简化可靠版）"""
        tail = content[-600:].lower()
        
        # 关键词：确认类提示
        confirm_kws = ['do you want to', 'do you want', 'proceed', 'confirm', 'continue']
        has_kw = any(kw in tail for kw in confirm_kws)
        
        # 选项：必须看到 1. 和 2. （或 ❯ 1.）
        has_options = ('1.' in tail and '2.' in tail) or '❯' in tail
        
        return has_kw and has_options
    
    # ==================== 核心修复：规则判断 ====================
    
    def rule_decision_with_confidence(self, content):
        """
        规则决策（修复版）
        返回: (is_certain, should_confirm, action, reason)
        """
        tail = content[-600:]
        tail_lower = tail.lower()
        
        # ===== 最高优先级：明确看到 "2. always allow" 类 =====
        if '2.' in tail and ('always' in tail_lower or 'don\'t ask' in tail_lower or '总是允许' in tail):
            return (True, True, "2", "规则：选项2是'始终允许'")
        
        # ===== 修复点：标准确认（Do you want to proceed + Yes/No）直接选1 =====
        # 看到 "Do you want" 或 "proceed" 且有 Yes/No 选项，直接确认选1
        if ('do you want' in tail_lower or 'proceed' in tail_lower):
            # 检查是否有标准 Yes/No 选项
            if re.search(r'1\.\s*yes', tail_lower) or re.search(r'❯\s*1\.\s*yes', tail_lower):
                # 确认这是标准确认（不是错误提示）
                if '2.' in tail or 'no' in tail_lower:
                    return (True, True, "1", "规则：标准确认对话框，选1(Yes)")
        
        # ===== 有菜单但规则不确定，交给AI =====
        if self.has_confirm_menu(content):
            if self.debug:
                print(f"[调试] 有确认菜单但规则不确定，{'发AI' if self.use_ai else '跳过'}")
            return (False, None, None, "规则不确定：有确认菜单但非标准格式")
        
        # ===== 无菜单 =====
        return (False, False, None, "无确认菜单")
    
    # ==================== AI决策（修复Prompt） ====================
    
    def ai_mode_decision(self, content, fingerprint):
        """AI模式：规则优先，不确定时发AI。返回5元组！"""
        # 1. 先调规则
        is_certain, should_confirm, action, reason = self.rule_decision_with_confidence(content)
        
        # 2. 规则确定 -> 直接用
        if is_certain:
            self.rule_direct_count += 1
            if should_confirm:
                if self.debug:
                    print(f"[调试] 规则直接确定：选{action}")
                return (True, action, f"[规则]{reason}", fingerprint, "rule_direct")
            else:
                return (False, "", reason, None, "rule_skip")
        
        # 3. 规则不确定但有菜单 -> 发AI
        if should_confirm is None and self.has_confirm_menu(content):
            return self._call_ai_api(content, fingerprint)
        
        # 4. 无菜单
        return (False, "", reason, None, "no_menu")
    
    def rule_mode_decision(self, content, fingerprint):
        """规则模式。返回5元组！"""
        is_certain, should_confirm, action, reason = self.rule_decision_with_confidence(content)
        
        if is_certain and should_confirm:
            return (True, action, f"[规则]{reason}", fingerprint, "confirm")
        else:
            return (False, "", reason, None, "uncertain")
    
    def _call_ai_api(self, content, fingerprint):
        """调用AI（修复版Prompt）。返回5元组！"""
        self.ai_call_count += 1
        screen_part = content[-600:]
        
        # ===== 关键修复：Prompt 明确指示 =====
        prompt = (
            "你是Claude Code自动确认助手。当前屏幕显示了一个确认对话框，请判断是否发送确认。\n\n"
            f"屏幕内容:\n```\n{screen_part}\n```\n\n"
            "重要判断标准:\n"
            "1. 如果看到'Do you want to proceed'、'Continue?'或'Confirm?'等确认提示，且有'1. Yes 2. No'选项，必须返回 should_confirm: true\n"
            "2. 标准确认对话框默认选择'1'（Yes）\n"
            "3. 如果看到'always allow'或'don't ask again'选项，选择'2'\n"
            "4. 如果看到错误信息、警告、或命令行提示符，返回 should_confirm: false\n\n"
            "请返回严格JSON格式:\n"
            "{\n"
            '  \"should_confirm\": true/false,\n'
            '  \"action\": \"1\"或\"2\",\n'
            '  \"reason\": \"简短判断原因\"\n'
            "}\n"
            "注意:对于'Do you want to proceed?'这种明确确认，action必须是\"1\""
        )
        
        if self.debug:
            print(f"[调试] 调用AI...")
        
        try:
            resp = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # 确定性最高
                    "max_tokens": 100
                },
                timeout=self.qwen_timeout
            )
            
            if resp.status_code == 200:
                result = resp.json()
                text = result['choices'][0]['message']['content']
                
                # 提取JSON（容错）
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    # 尝试从文本中提取JSON块
                    m = re.search(r'\{.*?"should_confirm".*?\}', text, re.DOTALL)
                    if m:
                        try:
                            parsed = json.loads(m.group(0))
                        except:
                            parsed = {}
                    else:
                        parsed = {}
                
                should = parsed.get("should_confirm", False)
                action = str(parsed.get("action", "1"))
                reason = parsed.get("reason", "AI判断")
                
                if self.debug:
                    print(f"[调试] AI返回: should={should}, action={action}, reason={reason}")
                
                if should:
                    return (True, action, f"[AI]{reason}", fingerprint, "ai_confirm")
                else:
                    return (False, f"[AI拒绝]{reason}", None, "ai_reject")
            else:
                return (False, f"API错误{resp.status_code}", None, "api_error")
        
        except requests.Timeout:
            return (False, "AI请求超时", None, "timeout")
        except Exception as e:
            return (False, f"AI异常:{str(e)[:20]}", None, "error")
    
    # ==================== 执行 ====================
    
    def execute_confirm(self, action, fingerprint):
        if self.is_processing:
            return False
        
        try:
            self.is_processing = True
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, action], 
                         check=False, timeout=1)
            time.sleep(0.05)
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, 'Enter'], 
                         check=False, timeout=1)
            
            self.last_confirm_time = time.time()
            self.confirm_count += 1
            self.mark_prompt_processed(fingerprint)
            
            print(f"[执行] 发送 '{action}' + 回车")
            return True
        except Exception as e:
            print(f"\n[错误] {e}")
            return False
        finally:
            self.is_processing = False
            time.sleep(0.5)
    
    def monitor_loop(self):
        mode_str = "AI模式" if self.use_ai else "规则模式"
        print("=" * 60)
        print(f"智能确认器 ({mode_str}) - 修复确认判断")
        print("=" * 60)
        print(f"[会话] {self.session_name}")
        print("[提示] 对'Do you want to proceed?'类提示已优化，默认选1")
        print("[停止] Ctrl+C")
        print("=" * 60)
        
        check_count = 0
        last_status = time.time()
        
        try:
            while self.running:
                check_count += 1
                
                if time.time() - last_status >= 10:
                    elapsed = int(time.time() - self.start_time)
                    extra = f" | 规则直达{self.rule_direct_count} | AI调用{self.ai_call_count}" if self.use_ai else ""
                    print(f"[状态] {elapsed}秒 | 确认{self.confirm_count} | 抑制{self.suppress_count} | 跳过{self.skip_count}{extra}")
                    last_status = time.time()
                    check_count = 0
                
                content = self.get_screen_content()
                if not content:
                    time.sleep(self.check_interval)
                    continue
                
                # 预筛选
                if self.is_in_cooldown():
                    self.suppress_count += 1
                    time.sleep(self.cooldown_interval)
                    continue
                
                fingerprint = self.compute_prompt_fingerprint(content)
                if self.is_prompt_processed(fingerprint):
                    self.skip_count += 1
                    time.sleep(self.check_interval)
                    continue
                
                if not self.has_confirm_menu(content):
                    self.skip_count += 1
                    time.sleep(self.check_interval)
                    continue
                
                # 决策
                if self.use_ai:
                    should, action, reason, fp, dtype = self.ai_mode_decision(content, fingerprint)
                else:
                    should, action, reason, fp, dtype = self.rule_mode_decision(content, fingerprint)
                
                if should and fp:
                    if not self.is_processing:
                        print(f"\n[触发] {reason} | 指纹:{fp[:8]}")
                        if self.execute_confirm(action, fp):
                            time.sleep(2)
                    else:
                        self.suppress_count += 1
                        left = self.cooldown_seconds - (time.time() - self.last_confirm_time)
                        print(f"[抑制] 冷却中(剩{left:.1f}s)")
                else:
                    self.skip_count += 1
                    if self.debug:
                        print(f"[跳过] {dtype}: {reason}")
                
                sleep_time = self.cooldown_interval if self.is_in_cooldown() else self.check_interval
                time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            pass
        finally:
            print(f"\n总结: 确认{self.confirm_count} | 抑制{self.suppress_count} | 跳过{self.skip_count}")
            if self.use_ai:
                print(f"规则直达: {self.rule_direct_count} | AI调用: {self.ai_call_count}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--ai", action="store_true", help="AI模式（规则优先）")
    parser.add_argument("--debug", action="store_true", help="调试输出（显示判断过程）")
    args = parser.parse_args()
    
    confirmer = SmartConfirmer(args.session, use_ai=args.ai, debug=args.debug)
    confirmer.monitor_loop()

if __name__ == "__main__":
    main()