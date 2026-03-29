#!/usr/bin/env python3
"""
智能确认器 - 统一架构版
AI模式调用规则模式的函数，规则不确定时才发AI
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
        
        # ==================== 统计变量 ====================
        self.running = True
        self.start_time = time.time()
        self.confirm_count = 0          # 成功确认次数
        self.suppress_count = 0         # 冷却期抑制次数
        self.skip_count = 0             # 无菜单跳过次数
        self.ai_call_count = 0          # AI实际调用次数（AI模式特有）
        self.rule_direct_count = 0      # 规则直接确定次数（AI模式特有）
        
        # ==================== 控制参数 ====================
        self.last_confirm_time = 0
        self.cooldown_seconds = 5
        self.is_processing = False
        
        # ==================== 重复检测 ====================
        self.processed_prompts = deque(maxlen=20)
    
    def load_env_config(self):
        """加载环境配置"""
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        self.api_url = os.getenv('QWEN_API_URL', 'http://192.168.0.70:5564/v1/chat/completions')
        self.model = os.getenv('QWEN_MODEL', '/opt/models/Qwen/Qwen3.5-27B-FP8')
        self.qwen_timeout = int(os.getenv('QWEN_TIMEOUT', '30'))
        
        # 检查间隔：2秒
        self.check_interval = 2
        self.cooldown_interval = 0.5
    
    # ==================== 公共基础设施 ====================
    
    def get_screen_content(self):
        """获取tmux屏幕内容"""
        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', self.session_name, '-p', '-J'],
                capture_output=True,
                text=True,
                timeout=2,
                check=True
            )
            return result.stdout
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
        """计算提示指纹（基于选项行）"""
        tail = content[-600:]
        lines = tail.split('\n')
        key_lines = []
        
        for line in lines:
            # 提取包含选项特征的行
            if re.search(r'[❯>\]]\s*\d+|\d+\.\s+(Yes|No|Always|是|否)', line, re.I):
                cleaned = re.sub(r'\s+', ' ', line.strip())
                if cleaned:
                    key_lines.append(cleaned)
        
        if len(key_lines) < 1:
            return None
        
        return hashlib.md5('|'.join(key_lines[-3:]).encode()).hexdigest()[:16]
    
    def is_in_cooldown(self):
        """检查是否在冷却期"""
        return (time.time() - self.last_confirm_time) < self.cooldown_seconds
    
    def is_prompt_processed(self, fingerprint):
        """检查是否5分钟内处理过"""
        if fingerprint is None:
            return False
        now = time.time()
        for stored_fp, ts in self.processed_prompts:
            if stored_fp == fingerprint and (now - ts) < 300:
                return True
        return False
    
    def mark_prompt_processed(self, fingerprint):
        """标记为已处理"""
        if fingerprint:
            self.processed_prompts.append((fingerprint, time.time()))
    
    def has_confirm_menu(self, content):
        """检测是否有确认菜单（关键词 + 选项）"""
        tail = content[-600:]
        
        # 关键词检测
        keywords = [r'Do you want', r'proceed', r'confirm', r'allow', 
                   r'continue', r'想要', r'确认', r'允许']
        has_kw = any(re.search(kw, tail, re.I) for kw in keywords)
        
        # 选项编号检测
        has_opt = bool(re.search(r'(\n\s*\d+\.\s|[❯>\]]\s*\d+)', tail))
        
        return has_kw and has_opt
    
    # ==================== 规则模式决策函数（公共） ====================
    
    def rule_decision_with_confidence(self, content):
        """
        规则模式决策，返回置信度
        
        返回: (is_certain, should_confirm, action, reason)
        
        is_certain=True:  规则能确定，直接执行（AI模式也会采用）
        is_certain=False: 规则不确定，需要AI判断（仅AI模式会走到这里）
        """
        tail = content[-600:]
        
        # ===== 高置信度场景1：明确看到 "2. always allow" 或类似 =====
        if re.search(r'2\.\s*(always allow|don\'t ask again|总是允许|不再询问)', tail, re.I):
            return (True, True, "2", "规则确定：选项2是'始终允许'")
        
        # ===== 高置信度场景2：明确看到 "1. Yes" 且没有 "always allow" 选项 =====
        # 即标准确认对话框，选1（默认允许）
        if (re.search(r'1\.\s*Yes', tail, re.I) and 
            not re.search(r'2\.\s*(always|don\'t ask)', tail, re.I)):
            return (True, True, "1", "规则确定：标准确认，选1")
        
        # ===== 中置信度：有菜单但看不清选哪个（需要AI）=====
        if self.has_confirm_menu(content):
            # 有菜单但规则不确定选哪个（比如只看到选项编号但没有明确关键词）
            return (False, None, None, "规则不确定：有确认菜单但选项不明确")
        
        # ===== 低置信度：没有菜单 =====
        return (False, False, None, "无确认菜单")
    
    # ==================== 模式专用决策 ====================
    
    def rule_mode_decision(self, content, fingerprint):
        """纯规则模式：只处理高置信度场景，不确定时不操作"""
        is_certain, should_confirm, action, reason = self.rule_decision_with_confidence(content)
        
        if is_certain and should_confirm:
            return (True, action, f"[规则]{reason}", fingerprint, "confirm")
        else:
            # 规则模式不确定时，直接跳过（不确认）
            return (False, "", reason, None, "rule_uncertain" if not is_certain else "no_match")
    
    def ai_mode_decision(self, content, fingerprint):
        """
        AI模式：先调用规则，规则不确定时才调用AI
        
        这是关键重构：AI模式复用规则函数，只在规则返回is_certain=False时发AI
        """
        # 第一步：调用规则模式函数（复用！）
        is_certain, should_confirm, action, reason = self.rule_decision_with_confidence(content)
        
        # 情况1：规则能确定 -> 直接用规则结果，不发AI（省token）
        if is_certain:
            self.rule_direct_count += 1
            if should_confirm:
                return (True, action, f"[规则确定]{reason}", fingerprint, "rule_direct")
            else:
                return (False, "", reason, None, "rule_reject")
        
        # 情况2：规则不确定但检测到菜单 -> 调用AI精细判断
        if should_confirm is None and self.has_confirm_menu(content):
            return self._call_ai_api(content, fingerprint)
        
        # 情况3：规则确定无菜单 -> 跳过
        return (False, "", reason, None, "no_menu")
    
    def _call_ai_api(self, content, fingerprint):
        """AI模式：调用LLM API（仅当规则不确定时走到这里）"""
        self.ai_call_count += 1
        
        screen_part = content[-600:]
        
        prompt = (
            "你是Claude Code自动确认助手。规则模式无法确定如何处理此提示，请帮忙判断。\n\n"
            f"屏幕内容：\n```\n{screen_part}\n```\n\n"
            "请返回JSON：\n"
            "{\n"
            '  \"should_confirm\": true/false,\n'
            '  \"action\": \"1\"/\"2\"/\"3\",\n'
            '  \"reason\": \"原因\"\n'
            "}\n"
            "注意：只在看到明确确认请求（如'Do you want to proceed'）时才返回true。"
        )
        
        try:
            resp = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 150
                },
                timeout=self.qwen_timeout
            )
            
            if resp.status_code == 200:
                result = resp.json()
                text = result['choices'][0]['message']['content']
                
                # 提取JSON
                try:
                    parsed = json.loads(text)
                except:
                    m = re.search(r'\{.*?\}', text, re.DOTALL)
                    parsed = json.loads(m.group(0)) if m else {}
                
                should = parsed.get("should_confirm", False)
                action = str(parsed.get("action", "1"))
                reason = parsed.get("reason", "AI判断")
                
                if should:
                    return (True, action, f"[AI]{reason}", fingerprint, "ai_confirm")
                else:
                    return (False, f"[AI拒绝]{reason}", None, "ai_reject")
            else:
                return (False, f"API错误{resp.status_code}", None, "api_error")
                
        except Exception as e:
            return (False, f"AI异常:{str(e)[:20]}", None, "error")
    
    # ==================== 执行与主循环 ====================
    
    def execute_confirm(self, action, fingerprint):
        """执行确认"""
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
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"\n[错误] {e}")
            return False
        finally:
            self.is_processing = False
    
    def monitor_loop(self):
        """主循环"""
        mode_str = "AI模式(规则优先)" if self.use_ai else "规则模式"
        print("=" * 60)
        print(f"智能确认器 ({mode_str})")
        print("=" * 60)
        print(f"[会话] {self.session_name} | [冷却期] {self.cooldown_seconds}秒 | [检查] 2秒/次")
        if self.use_ai:
            print("[策略] 规则确定→直接执行 | 规则不确定→调用AI")
        print("[停止] Ctrl+C")
        print("=" * 60)
        
        check_count = 0
        last_status = time.time()
        
        try:
            while self.running:
                check_count += 1
                
                # 每10秒输出状态
                if time.time() - last_status >= 10:
                    elapsed = int(time.time() - self.start_time)
                    extra = ""
                    if self.use_ai:
                        extra = f" | 规则直达{self.rule_direct_count} | AI调用{self.ai_call_count}"
                    print(f"[状态] {elapsed}秒 | 确认{self.confirm_count} | 抑制{self.suppress_count} | "
                          f"跳过{self.skip_count}{extra}")
                    last_status = time.time()
                    check_count = 0
                
                content = self.get_screen_content()
                if not content:
                    time.sleep(self.check_interval)
                    continue
                
                # 公共预筛选
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
                
                # 分模式决策（关键：AI模式调用rule_decision_with_confidence）
                if self.use_ai:
                    should, action, reason, fp, dtype = self.ai_mode_decision(content, fingerprint)
                else:
                    should, action, reason, fp, dtype = self.rule_mode_decision(content, fingerprint)
                
                # 执行
                if should and fp:
                    if not self.is_processing:
                        print(f"\n[触发] {reason} | 指纹:{fp[:8]}")
                        self.execute_confirm(action, fp)
                        time.sleep(2)
                    else:
                        self.suppress_count += 1
                else:
                    self.skip_count += 1
                    if self.debug:
                        print(f"[跳过] {reason}")
                
                time.sleep(self.cooldown_interval if self.is_in_cooldown() else self.check_interval)
        
        except KeyboardInterrupt:
            pass
        finally:
            self.print_summary()
    
    def print_summary(self):
        print("\n" + "=" * 60)
        print("运行总结")
        print("=" * 60)
        print(f"运行时长: {int(time.time() - self.start_time)}秒")
        print(f"成功确认: {self.confirm_count} 次")
        if self.use_ai:
            print(f"  ├─ 规则直接确定: {self.rule_direct_count} 次（未发AI）")
            print(f"  └─ AI判断确认: {self.confirm_count - self.rule_direct_count} 次")
            print(f"AI API调用: {self.ai_call_count} 次（仅规则不确定时）")
        print(f"冷却抑制: {self.suppress_count} 次")
        print(f"其他跳过: {self.skip_count} 次")
        print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Claude Code 智能确认器")
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--ai", action="store_true", help="AI模式（规则优先，不确定时发AI）")
    parser.add_argument("--cooldown", type=int, default=5, help="冷却期秒数")
    parser.add_argument("--debug", action="store_true", help="调试输出")
    args = parser.parse_args()
    
    confirmer = SmartConfirmer(args.session, use_ai=args.ai, debug=args.debug)
    if args.cooldown:
        confirmer.cooldown_seconds = args.cooldown
    
    confirmer.monitor_loop()

if __name__ == "__main__":
    main()