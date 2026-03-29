#!/usr/bin/env python3
"""
智能确认器 - 修复版
关键修复：
1. 简化确认检测，防止过度过滤
2. AI模式确保检测到菜单即调用（不再因"内容未变化"跳过）
3. 添加详细调试日志，可追踪决策过程
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
        self.debug = debug  # 调试模式开关
        
        self.load_env_config()
        
        # ==================== 统计变量（带详细注释） ====================
        self.running = True
        self.start_time = time.time()
        
        # confirm_count: 成功发送确认按键的次数（实际执行tmux send-keys且成功）
        self.confirm_count = 0
        
        # suppress_count: 检测到确认但处于冷却期（5秒内刚确认过）而抑制执行的次数
        self.suppress_count = 0
        
        # skip_count: 未检测到任何确认特征（命令行/普通日志/无菜单）而跳过的次数
        self.skip_count = 0
        
        # ai_call_count: AI模式特有，实际调用LLM API的次数（用于诊断）
        self.ai_call_count = 0
        
        # check_count: 当前10秒周期内执行的内容检查次数（用于计算实际轮询频率）
        self.check_count = 0
        
        # ==================== 防抖与状态控制 ====================
        self.last_confirm_time = 0
        self.cooldown_seconds = 5
        self.is_processing = False
        
        # ==================== 重复检测机制 ====================
        # processed_prompts: 已处理提示的指纹缓存队列，用于5分钟内去重防重复确认
        # 格式: [(fingerprint_hash, timestamp), ...]
        self.processed_prompts = deque(maxlen=20)
        
        # 内容追踪（仅AI模式用于决策后刷新，不再用于预筛选拦截）
        self.last_processed_fingerprint = None  # 最后处理成功的指纹，用于AI模式去重
    
    def load_env_config(self):
        """加载.env文件中的API配置"""
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
        
        self.api_url = os.getenv('QWEN_API_URL', 'http://192.168.0.70:5564/v1/chat/completions')
        self.model = os.getenv('QWEN_MODEL', '/opt/models/Qwen/Qwen3.5-27B-FP8')
        self.qwen_timeout = int(os.getenv('QWEN_TIMEOUT', '30'))
        
        # ==================== 轮询间隔配置 ====================
        # check_interval: 标准检查间隔（规则模式/AI模式通用），默认2秒
        self.check_interval = 2
        
        # cooldown_interval: 确认后冷却期内的快速轮询间隔（0.5秒），确保及时捕获新提示
        self.cooldown_interval = 0.5
    
    def get_screen_content(self):
        """获取tmux当前pane的屏幕内容（最后可见区域）"""
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
        """
        计算提示指纹（用于去重）
        提取屏幕最后800字符中，包含选项编号（1./2./❯）的关键行组合哈希
        """
        tail = content[-800:]
        lines = tail.split('\n')
        key_lines = []
        
        for line in lines:
            # 收集包含选项特征的行（1. 2. 3. 或 ❯）
            if re.search(r'[❯>\]]\s*\d+|\d+\.\s+(Yes|No|Always|是|否)', line, re.I):
                # 清理空格但保留文本特征
                cleaned = re.sub(r'\s+', ' ', line.strip())
                if cleaned:
                    key_lines.append(cleaned)
        
        if len(key_lines) < 1:
            return None
        
        # 用最后3行关键行生成指纹（足够区分不同提示）
        fingerprint = hashlib.md5('|'.join(key_lines[-3:]).encode()).hexdigest()[:16]
        return fingerprint
    
    def is_in_cooldown(self):
        """检查是否处于确认后的冷却期（防止连续误触）"""
        return (time.time() - self.last_confirm_time) < self.cooldown_seconds
    
    def is_prompt_processed(self, fingerprint):
        """检查该指纹是否在5分钟内已处理过（基于processed_prompts队列）"""
        if fingerprint is None:
            return False
        
        now = time.time()
        for stored_fp, timestamp in self.processed_prompts:
            if stored_fp == fingerprint and (now - timestamp) < 300:
                return True
        return False
    
    def mark_prompt_processed(self, fingerprint):
        """将指纹加入已处理队列，标记为5分钟内不再处理"""
        if fingerprint:
            self.processed_prompts.append((fingerprint, time.time()))
    
    def has_confirm_menu(self, content):
        """
        核心检测函数：检测是否有确认菜单（简化版，防止过度过滤）
        只要同时满足：确认关键词 + 选项编号（1./2./❯），即视为确认菜单
        """
        tail = content[-600:]  # 只看最后600字符（当前屏）
        
        # 1. 确认类关键词（放宽匹配）
        confirm_keywords = [
            r'Do you want to',
            r'proceed',
            r'confirm',
            r'allow',
            r'continue',
            r'想要',
            r'确认',
            r'允许',
            r'继续'
        ]
        has_keyword = any(re.search(kw, tail, re.I) for kw in confirm_keywords)
        
        # 2. 选项编号特征（必须看到 1./2. 或 ❯ 加数字）
        # 匹配：行首数字点、箭头加数字、或 ❯ 符号
        has_numbered_option = bool(re.search(
            r'(\n\s*\d+\.\s|[❯>\]]\s*\d+|^\s*\d+\.\s)', 
            tail, 
            re.MULTILINE
        ))
        
        if self.debug and has_keyword:
            print(f"[调试] 有关键词但{'无' if not has_numbered_option else '有'}选项编号")
        
        return has_keyword and has_numbered_option
    
    # ==================== 决策函数（关键修复） ====================
    
    def make_decision(self, content):
        """
        统一决策入口（修复版逻辑）
        顺序：冷却期 -> 指纹查重 -> 菜单检测 -> [AI模式:调用AI] / [规则模式:直接判断]
        
        返回: (should_confirm, action, reason, fingerprint, decision_type)
        """
        # 1. 冷却期检查（最高优先级，防止连击）
        if self.is_in_cooldown():
            return (False, "", "冷却期内", None, "cooldown")
        
        # 2. 指纹查重（5分钟内处理过的相同提示不再处理）
        fingerprint = self.compute_prompt_fingerprint(content)
        if self.is_prompt_processed(fingerprint):
            return (False, "", f"5分钟内已处理过({fingerprint[:6]})", fingerprint, "duplicate")
        
        # 3. 确认菜单检测（核心：有关键词+选项编号？）
        if not self.has_confirm_menu(content):
            return (False, "", "未检测到确认菜单(无关键词或选项)", None, "no_menu")
        
        # 4. 分模式处理（关键修复：AI模式不再检查"内容是否变化"，而是直接调用）
        if self.use_ai:
            # AI模式：只要有菜单就调用AI（除非指纹重复，上面已查）
            return self._ai_decision(content, fingerprint)
        else:
            # 规则模式：直接判断选1还是2
            return self._rule_decision(content, fingerprint)
    
    def _rule_decision(self, content, fingerprint):
        """规则模式：基于正则快速判断选项"""
        tail = content[-600:]
        
        # 检测"always allow"类选项通常在位置2
        if re.search(r'2\.\s*.*(always|don\'t ask|总是|不再|remember)', tail, re.I):
            action = "2"
            reason = "规则:选择'始终允许'(选项2)"
        else:
            action = "1"
            reason = "规则:选择默认选项(选项1)"
        
        return (True, action, reason, fingerprint, "confirm")
    
    def _ai_decision(self, content, fingerprint):
        """
        AI模式精细决策（关键修复：确保一定会调用API，除非网络错误）
        输入: 已确定有确认菜单的屏幕内容
        输出: 经LLM确认后的决策
        """
        self.ai_call_count += 1
        
        screen_part = content[-600:]  # 发给AI的内容（与检测范围一致）
        
        # 构造明确的Prompt，要求JSON返回
        prompt_text = (
            "你是Claude Code自动确认助手。当前屏幕显示了一个确认对话框，请判断是否应该确认。\n\n"
            f"屏幕内容:\n```\n{screen_part}\n```\n\n"
            "请分析这是否是真正的用户确认请求（而非错误信息或日志），并选择操作。\n"
            "返回严格JSON格式:\n"
            "{\n"
            '  \"should_confirm\": true/false,\n'
            '  \"action\": \"1\"或\"2\"或\"3\",\n'
            '  \"reason\": \"简短原因(如:确认删除/允许编辑/拒绝)\"\n'
            "}\n\n"
            "判断标准:\n"
            "- 如果是'Do you want to proceed/continue/allow'类确认，返回true\n"
            "- 如果有'always allow/don't ask again'选项，action选\"2\"\n"
            "- 如果是错误提示或危险操作（如删除生产环境），返回false"
        )
        
        if self.debug:
            print(f"[调试] 调用AI API (第{self.ai_call_count}次)...")
        
        try:
            resp = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "temperature": 0.1,
                    "max_tokens": 150
                },
                timeout=self.qwen_timeout
            )
            
            if resp.status_code == 200:
                result = resp.json()
                text = result['choices'][0]['message']['content']
                
                # 提取JSON（容错处理）
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    # 尝试从markdown代码块提取
                    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
                    if m:
                        parsed = json.loads(m.group(1))
                    else:
                        # 再尝试直接找大括号内容
                        m = re.search(r'\{.*?\}', text, re.DOTALL)
                        parsed = json.loads(m.group(0)) if m else {}
                
                should = parsed.get("should_confirm", False)
                action = str(parsed.get("action", "1"))
                reason = parsed.get("reason", "AI判断")
                
                if should:
                    return (True, action, f"AI确认:{reason}", fingerprint, "confirm")
                else:
                    return (False, f"AI拒绝:{reason}", None, "ai_reject")
            else:
                # API错误时保守处理（不确认）
                return (False, "", f"API错误({resp.status_code})", None, "api_error")
        
        except requests.Timeout:
            return (False, "", "AI请求超时", None, "timeout")
        except Exception as e:
            return (False, "", f"AI异常:{str(e)[:30]}", None, "error")
    
    # ==================== 执行函数 ====================
    
    def execute_confirm(self, action, fingerprint):
        """向tmux发送确认按键"""
        if self.is_processing:
            return False
        
        try:
            self.is_processing = True
            
            # 发送数字键
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, action], 
                check=False, 
                timeout=1
            )
            time.sleep(0.05)
            # 发送回车
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, 'Enter'], 
                check=False, 
                timeout=1
            )
            
            self.last_confirm_time = time.time()
            self.confirm_count += 1
            self.mark_prompt_processed(fingerprint)
            
            print(f"[执行] 已发送 '{action}' + 回车")
            time.sleep(0.5)
            return True
            
        except Exception as e:
            print(f"\n[错误] 发送失败: {e}")
            return False
        finally:
            self.is_processing = False
    
    # ==================== 主循环 ====================
    
    def monitor_loop(self):
        """监控主循环（2秒检查间隔，10秒状态输出）"""
        mode_str = "AI模式" if self.use_ai else "规则模式"
        print("=" * 60)
        print(f"智能确认器 ({mode_str}) - 检查间隔2秒")
        print("=" * 60)
        print(f"[会话] {self.session_name} | [冷却期] {self.cooldown_seconds}秒")
        print("[统计] 确认=已执行 | 抑制=冷却中跳过 | 跳过=无菜单 | AI=API调用次数")
        if self.debug:
            print("[调试] 调试模式开启，将显示详细决策过程")
        print("[停止] 按 Ctrl+C 停止")
        print("=" * 60)
        
        last_status = time.time()
        
        try:
            while self.running:
                self.check_count += 1
                now = time.time()
                
                # 每10秒输出一次统计状态
                if now - last_status >= 10:
                    elapsed = int(now - self.start_time)
                    avg_interval = 10.0 / self.check_count if self.check_count > 0 else 0
                    ai_info = f" | AI调用{self.ai_call_count}次" if self.use_ai else ""
                    print(f"[状态] {elapsed}秒 | 确认{self.confirm_count} | 抑制{self.suppress_count} | "
                          f"跳过{self.skip_count}{ai_info} | {self.check_count}次/10秒")
                    last_status = now
                    self.check_count = 0
                
                # 获取屏幕
                content = self.get_screen_content()
                if not content:
                    time.sleep(self.check_interval)
                    continue
                
                # 决策（关键修复后的统一入口）
                should, action, reason, fingerprint, decision_type = self.make_decision(content)
                
                if should:
                    # 检测到需要确认
                    if not self.is_processing and not self.is_in_cooldown():
                        print(f"\n[触发] {reason} | 指纹:{fingerprint[:8] if fingerprint else 'N/A'}")
                        self.execute_confirm(action, fingerprint)
                        time.sleep(2)  # 确认后等待界面刷新
                    else:
                        # 冷却期内检测到，计入抑制
                        self.suppress_count += 1
                        left = self.cooldown_seconds - (time.time() - self.last_confirm_time)
                        print(f"[抑制] {reason} (冷却期剩余{left:.1f}秒)")
                else:
                    # 不需要确认，根据类型统计
                    if decision_type == "cooldown":
                        self.suppress_count += 1
                    else:
                        self.skip_count += 1
                        if self.debug and decision_type not in ["no_menu", "duplicate"]:
                            print(f"[调试跳过] {reason}")
                
                # 动态间隔：冷却期内0.5秒快速检查，否则2秒
                sleep_time = self.cooldown_interval if self.is_in_cooldown() else self.check_interval
                time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            pass
        finally:
            self.print_summary()
    
    def print_summary(self):
        """打印运行总结"""
        elapsed = int(time.time() - self.start_time)
        total = self.confirm_count + self.suppress_count + self.skip_count
        
        print("\n" + "=" * 60)
        print("运行总结")
        print("=" * 60)
        print(f"运行时长: {elapsed}秒 | 总计检查: {total}次")
        print(f"成功确认: {self.confirm_count} 次")
        print(f"冷却抑制: {self.suppress_count} 次 (检测到但处于5秒冷却期)")
        print(f"常规跳过: {self.skip_count} 次 (未检测到确认菜单)")
        if self.use_ai:
            print(f"AI API调用: {self.ai_call_count} 次")
            print(f"AI命中率: {self.confirm_count}/{self.ai_call_count} (即AI判断为true的比例)")
        print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Claude Code 智能确认器")
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--ai", action="store_true", help="使用AI模式（检测到菜单即调用LLM）")
    parser.add_argument("--cooldown", type=int, default=5, help="确认后冷却期(秒)")
    parser.add_argument("--debug", action="store_true", help="开启调试输出（显示每次跳过的原因）")
    args = parser.parse_args()
    
    confirmer = SmartConfirmer(
        args.session, 
        use_ai=args.ai, 
        debug=args.debug
    )
    if args.cooldown:
        confirmer.cooldown_seconds = args.cooldown
    
    confirmer.monitor_loop()


if __name__ == "__main__":
    main()