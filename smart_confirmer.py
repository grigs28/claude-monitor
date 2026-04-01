#!/usr/bin/env python3
"""
智能确认器 - 自动响应 tmux 中 Claude Code 的权限确认提示
"""

import subprocess
import requests
import time
import json
import sys
import argparse
import os
import signal
import re
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
        self.last_confirm_time = 0

        self.stop_file = Path(__file__).parent / '.stop'
        self.pid_file = Path(__file__).parent / '.pid'

        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)

        self.cooldown = int(os.getenv('COOLDOWN', '2'))
        self.rule_context_size = int(os.getenv('RULE_CONTEXT_SIZE', '1000'))
        self.heartbeat_interval = int(os.getenv('HEARTBEAT_INTERVAL', '60'))

        if use_ai:
            self.api_url = os.getenv('QWEN_API_URL', 'http://192.168.0.70:5564/v1/chat/completions')
            self.model = os.getenv('QWEN_MODEL', '/opt/models/Qwen/Qwen3.5-27B-FP8')
            self.timeout = int(os.getenv('QWEN_TIMEOUT', '30'))
            self.ai_context_size = int(os.getenv('AI_CONTEXT_SIZE', '300'))
    
    def get_screen(self):
        try:
            # 截取最后 N 个字符用于规则匹配
            r = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p', '-J'],
                             capture_output=True, text=True, timeout=1)
            content = r.stdout
            if len(content) > self.rule_context_size:
                content = content[-self.rule_context_size:]
            return content
        except Exception as e:
            print(f"[错误] {e}")
            return ""
    
    def detect(self, text):
        """关键词检测，规则和AI共用"""
        t = text.lower()
        return {
            'approval': 'requires approval' in t,
            'do_you': 'do you want' in t,
            'proceed': 'proceed' in t,
            'option1': '1.' in text,
            'arrow': '❯' in text,
            'yes': 'yes' in t,
            'option2': '2.' in text,
            'always': 'always' in t or "don't ask" in t or "'t ask" in t or "'t ask" in t,
            'no': 'no' in t,
        }

    def should_confirm(self, text):
        """
        统一判断逻辑：规则优先，AI兜底
        返回: (should, action, reason)
        """
        d = self.detect(text)
        has_prompt = d['approval'] or d['do_you'] or d['proceed']
        has_options = d['option1'] or d['arrow'] or (d['yes'] and d['no'])

        # 规则：明确提示 + 选项
        if has_prompt and has_options:
            if d['option2'] and d['always']:
                return True, "2", "规则:always"
            return True, "1", "规则:yes"

        # AI兜底：有选项但规则不认识
        if self.use_ai and has_options:
            return self.ask_ai(text, d)

        return False, None, "无匹配"

    def ask_ai(self, text, detected):
        """AI兜底判断，接收规则检测结果"""
        self.ai_count += 1
        print(f"[AI] 调用 | 检测={detected}")

        prompt = (
            f"判断是否需要确认。屏幕内容：\n```\n" + text[-self.ai_context_size:] + "\n```\n"
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
                print(f"[AI] 结果 confirm={confirm}, action={action}")
                return confirm, action, "AI"
            else:
                print(f"[AI] HTTP {r.status_code}")
                return False, None, "api错误"
        except Exception as e:
            print(f"[AI] 异常 {e}")
            return False, None, "异常"
    
    def send(self, key):
        try:
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, key],
                          check=False, timeout=1)
            time.sleep(0.05)
            subprocess.run(['tmux', 'send-keys', '-t', self.session_name, 'Enter'],
                          check=False, timeout=1)
            self.confirm_count += 1
            self.last_confirm_time = time.time()
            return True
        except Exception as e:
            print(f"  [发送失败] {e}")
            return False

    def stop(self, signum=None, frame=None):
        self.running = False

    def cleanup(self):
        self.pid_file.unlink(missing_ok=True)
        self.stop_file.unlink(missing_ok=True)

    def run(self):
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        self.pid_file.write_text(str(os.getpid()))
        self.stop_file.unlink(missing_ok=True)

        mode = "规则+AI" if self.use_ai else "纯规则"
        print(f"[启动] 智能确认器 ({mode}) | 会话: {self.session_name} | 冷却: {self.cooldown}s | PID: {os.getpid()}")
        print(f"[停止] kill {os.getpid()} 或 touch {self.stop_file}")

        last_screen = ""
        last_output_time = time.time()

        try:
            while self.running:
                if self.stop_file.exists():
                    self.stop()
                    break

                # 冷却期
                elapsed = time.time() - self.last_confirm_time
                if elapsed < self.cooldown:
                    wait = self.cooldown - elapsed
                    while wait > 0 and self.running:
                        time.sleep(min(wait, 0.5))
                        wait = self.cooldown - (time.time() - self.last_confirm_time)
                    if not self.running:
                        break

                # 获取屏幕
                text = self.get_screen()
                if not text:
                    if time.time() - last_output_time >= self.heartbeat_interval:
                        print(f"[等待] 屏幕为空 | 确认{self.confirm_count}次")
                        last_output_time = time.time()
                    time.sleep(1)
                    continue

                # 检测屏幕变化
                screen_stripped = text.rstrip()
                last_screen = screen_stripped

                # 判断
                should, action, reason = self.should_confirm(text)

                if should:
                    print(f"[确认] 第{self.confirm_count + 1}次 | 动作={action} | {reason}")
                    if self.send(action):
                        print(f"[成功] 已确认{self.confirm_count}次" + (f"，AI{self.ai_count}次" if self.use_ai else ""))
                        time.sleep(1.5)
                    else:
                        time.sleep(0.5)
                    last_output_time = time.time()
                else:
                    if time.time() - last_output_time >= self.heartbeat_interval:
                        print(f"[监控] 确认{self.confirm_count}次" + (f"，AI{self.ai_count}次" if self.use_ai else "") + " | 无变化")
                        last_output_time = time.time()
                    time.sleep(1)
        finally:
            self.cleanup()
            print(f"[退出] 确认{self.confirm_count}次" + (f"，AI{self.ai_count}次" if self.use_ai else ""))


class HookHandler:
    """PermissionRequest Hook 处理器，基于工具名和命令判断 allow/deny"""

    # 硬编码规则
    DENY_COMMANDS = [
        r'rm\s+-rf\s+/',
        r':\(\)\{.*:\|:&\}',
        r'dd\s+if=.*of=/dev/',
        r'curl\b.*\|\s*(ba)?sh',
        r'wget\b.*\|\s*(ba)?sh',
        r'mkfs\.?',
        r'iptables\b',
        r'chmod\s+-R\s+777\s+/',
        r'shutdown\b',
        r'reboot\b',
    ]

    DENY_PATHS = ['/etc/', '/boot/', '/sys/', '/proc/']

    ALLOW_TOOLS = {'Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch', 'mcp__*'}

    ALLOW_COMMANDS = [
        r'git\s+(status|log|diff|branch|show|tag|remote|stash|blame)',
        r'ls\b',
        r'cat\b',
        r'head\b',
        r'tail\b',
        r'pwd\b',
        r'whoami\b',
        r'which\b',
        r'echo\b',
        r'find\b',
        r'python\d?\s+-c\s+"import\s+py_compile',
        r'npm\s+(test|run|lint|install)',
        r'pytest\b',
        r'make\b',
    ]

    def __init__(self, use_ai=False):
        self.use_ai = use_ai

        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)

        if use_ai:
            self.api_url = os.getenv('QWEN_API_URL', 'http://192.168.0.70:5564/v1/chat/completions')
            self.model = os.getenv('QWEN_MODEL', '/opt/models/Qwen/Qwen3.5-27B-FP8')
            self.timeout = int(os.getenv('QWEN_TIMEOUT', '30'))
            self.ai_context_size = int(os.getenv('AI_CONTEXT_SIZE', '1000'))

        self.user_deny = self._load_patterns('HOOK_DENY_PATTERNS')
        self.user_allow = self._load_patterns('HOOK_ALLOW_PATTERNS')
        self.log_file = os.getenv('HOOK_LOG_FILE') or str(Path(__file__).parent / 'hook.log')

    def _load_patterns(self, env_var):
        val = os.getenv(env_var, '')
        return [p.strip() for p in val.split(',') if p.strip()]

    def _log(self, tool_name, decision, reason):
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"[{ts}] {decision} | {tool_name} | {reason}\n")
        except Exception:
            pass

    def _output(self, behavior, message=None):
        result = {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": behavior}}}
        if message:
            result["hookSpecificOutput"]["decision"]["message"] = message
        print(json.dumps(result, ensure_ascii=False))
        self._log(self._current_tool, behavior, message or behavior)

    def _match_any(self, text, patterns):
        for p in patterns:
            if re.search(p, text):
                return True
        return False

    def check_deny(self, tool_name, tool_input):
        """检查拒绝规则，返回原因或 None"""
        # Bash 命令检查
        if tool_name == 'Bash':
            cmd = tool_input.get('command', '')
            # 硬编码拒绝
            for pattern in self.DENY_COMMANDS:
                if re.search(pattern, cmd):
                    return f"危险命令: {pattern}"
            # 用户自定义拒绝
            for p in self.user_deny:
                if re.search(p, cmd):
                    return f"用户拒绝规则: {p}"

        # 危险路径检查（Write/Edit）
        if tool_name in ('Write', 'Edit'):
            path = tool_input.get('file_path', '')
            for dp in self.DENY_PATHS:
                if path.startswith(dp):
                    return f"危险路径: {path}"

        return None

    def check_allow(self, tool_name, tool_input):
        """检查允许规则，返回原因或 None"""
        # 安全工具直接允许
        if tool_name in self.ALLOW_TOOLS:
            return f"安全工具: {tool_name}"

        # Bash 命令检查
        if tool_name == 'Bash':
            cmd = tool_input.get('command', '')
            # 硬编码允许
            for pattern in self.ALLOW_COMMANDS:
                if re.search(pattern, cmd):
                    return f"允许命令: {pattern}"
            # 用户自定义允许
            for p in self.user_allow:
                if re.search(p, cmd):
                    return f"用户允许规则: {p}"

        return None

    def _ai_decide(self, tool_name, tool_input):
        """AI 兜底判断"""
        context = json.dumps({"tool_name": tool_name, "tool_input": tool_input}, ensure_ascii=False)
        if len(context) > self.ai_context_size:
            context = context[-self.ai_context_size:]

        prompt = (
            f"判断以下工具调用是否应该被允许。\n"
            f"工具调用：\n```\n{context}\n```\n"
            "读写代码文件、运行测试、git操作通常是安全的。"
            "删除文件、网络服务操作、系统管理操作通常不安全。\n"
            "JSON: {\"allow\":true/false,\"reason\":\"简短原因\"}"
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
                content = r.json()['choices'][0]['message']['content']
                allow = '"allow":true' in content.replace(' ', '').lower()
                # 提取 reason
                import re as _re
                m = _re.search(r'"reason"\s*:\s*"([^"]*)"', content)
                reason = m.group(1) if m else "AI判断"
                if allow:
                    self._output("allow", f"AI: {reason}")
                else:
                    self._output("deny", f"AI: {reason}")
            else:
                self._log(tool_name, "跳过", f"AI HTTP {r.status_code}")
        except Exception as e:
            self._log(tool_name, "跳过", f"AI异常: {e}")

    def run_hook(self):
        """主入口：读 stdin JSON → 规则判断 → AI兜底 → 输出"""
        if sys.stdin.isatty():
            print("[Hook模式] 从 stdin 读取 JSON，由 Claude Code 自动调用。")
            print("手动测试:")
            print('  echo \'{"tool_name":"Bash","tool_input":{"command":"git status"}}\' | python3 smart_confirmer.py --hook')
            sys.exit(1)

        raw = sys.stdin.read()
        if not raw.strip():
            print("[Hook模式] 从 stdin 读取 JSON，由 Claude Code 自动调用。")
            print("手动测试:")
            print('  echo \'{"tool_name":"Bash","tool_input":{"command":"git status"}}\' | python3 smart_confirmer.py --hook')
            sys.exit(1)

        try:
            input_data = json.loads(raw)
        except json.JSONDecodeError:
            print(f"[Hook模式] JSON 解析失败: {raw[:100]}")
            sys.exit(1)

        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})
        self._current_tool = tool_name

        # 1. 拒绝规则
        deny_reason = self.check_deny(tool_name, tool_input)
        if deny_reason:
            self._output("deny", deny_reason)
            return

        # 2. 允许规则
        allow_reason = self.check_allow(tool_name, tool_input)
        if allow_reason:
            self._output("allow", allow_reason)
            return

        # 3. AI 兜底
        if self.use_ai:
            self._ai_decide(tool_name, tool_input)
            return

        # 4. 无匹配，走默认流程
        self._log(tool_name, "默认", "无匹配规则")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智能确认器 - 自动响应 Claude Code 权限确认提示")
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--tmux", action="store_true", help="tmux 轮询模式")
    parser.add_argument("--hook", action="store_true", help="PermissionRequest Hook 模式")
    parser.add_argument("--ai", action="store_true", help="AI 兜底")
    args = parser.parse_args()

    if args.hook:
        HookHandler(use_ai=args.ai).run_hook()
    elif args.tmux:
        FixConfirmer(args.session, use_ai=args.ai).run()
    else:
        parser.print_help()
        print("\n错误: 请指定运行模式 (--tmux 或 --hook)")
        sys.exit(1)