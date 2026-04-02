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
import shutil
import threading
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
        self.stop_event = threading.Event()

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
            'option1': re.search(r'(^|\s)1\.\s', text) is not None,
            'arrow': '❯' in text,
            'yes': 'yes' in t,
            'option2': re.search(r'(^|\s)2\.\s', text) is not None,
            'always': 'always' in t or "don't ask" in t or "'t ask" in t,
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
            r = subprocess.run(['tmux', 'send-keys', '-t', self.session_name, 'Enter'],
                          check=False, timeout=1)
            if r.returncode != 0:
                print(f"  [发送失败] tmux send-keys 返回 {r.returncode}")
                return False
            self.confirm_count += 1
            self.last_confirm_time = time.time()
            return True
        except Exception as e:
            print(f"  [发送失败] {e}")
            return False

    def stop(self, signum=None, frame=None):
        self.running = False
        self.stop_event.set()

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

        last_output_time = time.time()

        try:
            while self.running and not self.stop_event.is_set():
                if self.stop_file.exists():
                    self.stop()
                    break

                # 冷却期
                elapsed = time.time() - self.last_confirm_time
                if elapsed < self.cooldown:
                    wait = self.cooldown - elapsed
                    while wait > 0 and self.running and not self.stop_event.is_set():
                        self.stop_event.wait(min(wait, 0.5))
                        wait = self.cooldown - (time.time() - self.last_confirm_time)
                    if not self.running or self.stop_event.is_set():
                        break

                # 获取屏幕
                text = self.get_screen()
                if not text:
                    if time.time() - last_output_time >= self.heartbeat_interval:
                        print(f"[等待] 屏幕为空 | 确认{self.confirm_count}次")
                        last_output_time = time.time()
                    self.stop_event.wait(1)
                    continue

                # 判断
                should, action, reason = self.should_confirm(text)

                if should:
                    print(f"[确认] 第{self.confirm_count + 1}次 | 动作={action} | {reason}")
                    if self.send(action):
                        print(f"[成功] 已确认{self.confirm_count}次" + (f"，AI{self.ai_count}次" if self.use_ai else ""))
                        self.stop_event.wait(1.5)
                    else:
                        self.stop_event.wait(0.5)
                    last_output_time = time.time()
                else:
                    if time.time() - last_output_time >= self.heartbeat_interval:
                        print(f"[监控] 确认{self.confirm_count}次" + (f"，AI{self.ai_count}次" if self.use_ai else "") + " | 无变化")
                        last_output_time = time.time()
                    self.stop_event.wait(1)
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
        r'mkfs\b',
        r'iptables\b',
        r'chmod\s+-R\s+777\s+/',
        r'shutdown\b',
        r'reboot\b',
    ]

    DENY_PATHS = ['/etc/', '/boot/', '/sys/', '/proc/']

    ALLOW_TOOLS = {'Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch'}

    ALLOW_COMMANDS = [
        r'git\s+(status|log|diff|branch|show|tag|remote|stash|blame)',
        r'ls\b',
        r'cat\b',
        r'head\b',
        r'tail\b',
        r'pwd\b',
        r'whoami\b',
        r'which\b',
        r'echo\s+(?!.*[>|])',
        r'find\b',
        r'python\d?\s+-c\s+"import\s+py_compile',
        r'npm\s+(test|run|lint|install)',
        r'pytest\b',
        r'make\b',
    ]

    def __init__(self, use_ai=False, allow_all=False):
        self.use_ai = use_ai
        self.allow_all = allow_all

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

    def _reset_fallback_count(self):
        """PermissionRequest 触发说明当前模型正常，重置 fallback 失败计数和激活状态"""
        count_file = Path(__file__).parent / '.fallback_count'
        active_file = Path(__file__).parent / '.fallback_active'
        count_file.unlink(missing_ok=True)
        active_file.unlink(missing_ok=True)

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
        # 仅在 allow 时重置 fallback 计数（deny 不代表模型正常）
        if behavior == "allow":
            self._reset_fallback_count()

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
        # 截断过长的输入值，保持 JSON 结构完整
        max_val_len = self.ai_context_size // 2
        truncated = {}
        for k, v in tool_input.items():
            s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            if len(s) > max_val_len:
                truncated[k] = s[:max_val_len] + '...(truncated)'
            else:
                truncated[k] = v
        context = json.dumps({"tool_name": tool_name, "tool_input": truncated}, ensure_ascii=False)

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
                allow = bool(re.search(r'"allow"\s*:\s*true', content, re.IGNORECASE))
                m = re.search(r'"reason"\s*:\s*"([^"]*)"', content)
                reason = m.group(1) if m else "AI判断"
                if allow:
                    self._output("allow", f"AI: {reason}")
                else:
                    self._output("deny", f"AI: {reason}")
            else:
                self._log(tool_name, "deny", f"AI HTTP {r.status_code}")
                self._output("deny", f"AI HTTP错误: {r.status_code}")
        except Exception as e:
            self._log(tool_name, "deny", f"AI异常: {e}")
            self._output("deny", f"AI异常")

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

        # 2. 全部允许
        if self.allow_all:
            self._output("allow", f"allow-all 模式: {tool_name}")
            return

        # 3. 允许规则
        allow_reason = self.check_allow(tool_name, tool_input)
        if allow_reason:
            self._output("allow", allow_reason)
            return

        # 4. AI 兜底
        if self.use_ai:
            self._ai_decide(tool_name, tool_input)
            return

        # 5. 无匹配，走默认流程
        self._log(tool_name, "默认", "无匹配规则")


class FallbackHandler:
    """处理 StopFailure 事件，连续失败达阈值后切换到备用模型"""

    # 这些错误类型计入失败次数
    COUNTED_ERRORS = {'rate_limit', 'authentication_failed', 'billing_error',
                      'server_error', 'unknown'}

    def __init__(self, threshold=3):
        config_path = Path(__file__).parent / '.model_schedules.json'
        if not config_path.exists():
            print("[Fallback] 错误: .model_schedules.json 不存在", file=sys.stderr)
            self.fallback_models = []
            self.default_env = {}
            self.schedules = []
            self.settings_path = Path.home() / '.claude' / 'settings.json'
        else:
            with open(config_path) as f:
                cfg = json.load(f)
            self.fallback_models = cfg.get('fallback_models', [])
            self.default_env = cfg.get('default', {})
            self.schedules = cfg.get('schedules', [])
            self.settings_path = Path(os.path.expanduser(cfg.get('settings_path', '~/.claude/settings.json')))

        self.threshold = threshold
        self.count_file = Path(__file__).parent / '.fallback_count'
        self.active_file = Path(__file__).parent / '.fallback_active'

    def get_count(self):
        try:
            return int(self.count_file.read_text().strip())
        except Exception:
            return 0

    def set_count(self, n):
        self.count_file.write_text(str(n))

    def is_active(self):
        return self.active_file.exists()

    def set_active(self, model_name):
        self.active_file.write_text(model_name)

    def clear_active(self):
        self.active_file.unlink(missing_ok=True)

    def handle_stop_failure(self, error_type):
        """处理 StopFailure 事件，返回是否触发了切换"""
        if error_type not in self.COUNTED_ERRORS:
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [Fallback] 错误类型 '{error_type}' 不计入失败", file=sys.stderr)
            return False

        # 已在备用模型上，不重复切换
        if self.is_active():
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [Fallback] 已在备用模型上，跳过", file=sys.stderr)
            return False

        count = self.get_count() + 1
        self.set_count(count)
        ts = time.strftime('%H:%M:%S')
        print(f"[{ts}] [Fallback] 连续失败 {count}/{self.threshold} (错误: {error_type})", file=sys.stderr)

        if count >= self.threshold:
            return self._do_switch()
        return False

    def _do_switch(self):
        try:
            with open(self.settings_path) as f:
                settings = json.load(f)
        except Exception as e:
            print(f"[Fallback] 读取 settings.json 失败: {e}", file=sys.stderr)
            return False

        current_model = settings.get('env', {}).get('ANTHROPIC_DEFAULT_OPUS_MODEL', '')

        # 1. 先尝试切换到当前时间对应的 schedule 或 default
        target_env, target_name = self._get_schedule_env()
        target_model = target_env.get('ANTHROPIC_DEFAULT_OPUS_MODEL', '')

        if target_model and target_model != current_model:
            bak = self.settings_path.with_suffix('.json.bak')
            try:
                shutil.copy2(self.settings_path, bak)
            except Exception:
                pass

            merged_env = dict(settings.get('env', {}))
            merged_env.update(target_env)
            settings['env'] = merged_env
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            self.set_count(0)
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [Fallback] 已切换到时间表模型: {target_name}", file=sys.stderr)
            return True

        # 2. 时间表模型也失败，尝试 fallback_models
        if not self.fallback_models:
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [Fallback] 时间表模型 {target_name} 已失败，无备用模型", file=sys.stderr)
            return False

        for fb in sorted(self.fallback_models, key=lambda x: x.get('priority', 99)):
            fb_env = fb['env']
            fb_name = fb['name']

            if current_model == fb_env.get('ANTHROPIC_DEFAULT_OPUS_MODEL'):
                ts = time.strftime('%H:%M:%S')
                print(f"[{ts}] [Fallback] 已在备用模型 {fb_name} 上", file=sys.stderr)
                self.set_active(fb_name)
                return False

            bak = self.settings_path.with_suffix('.json.bak')
            try:
                shutil.copy2(self.settings_path, bak)
            except Exception:
                pass

            merged_env = dict(settings.get('env', {}))
            merged_env.update(fb_env)
            settings['env'] = merged_env
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

            self.set_active(fb_name)
            self.set_count(0)
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [Fallback] 时间表模型已失败，切换到备用模型: {fb_name}", file=sys.stderr)
            return True

        ts = time.strftime('%H:%M:%S')
        print(f"[{ts}] [Fallback] 所有模型均已尝试且失败", file=sys.stderr)
        return False

    def _get_schedule_env(self):
        """获取当前时间对应的 schedule 或 default 配置"""
        now = time.localtime()
        now_min = now.tm_hour * 60 + now.tm_min
        for s in self.schedules:
            start = int(s['start'].split(':')[0]) * 60 + int(s['start'].split(':')[1])
            end = int(s['end'].split(':')[0]) * 60 + int(s['end'].split(':')[1])
            if start <= end:
                if start <= now_min < end:
                    return s['env'], s['name']
            else:  # crosses midnight
                if now_min >= start or now_min < end:
                    return s['env'], s['name']
        return self.default_env, '默认'

    def reset(self):
        """手动重置失败计数和激活状态"""
        self.set_count(0)
        self.clear_active()
        print("[Fallback] 已重置", file=sys.stderr)


class ModelSwitcher(threading.Thread):
    """后台线程：根据时间段切换 Claude settings.json 模型配置，仅在 Claude 未调用模型时修改"""

    def __init__(self, session_name, stop_event):
        super().__init__(daemon=True)
        self.session_name = session_name
        self.stop_event = stop_event
        self.fallback_active_file = Path(__file__).parent / '.fallback_active'

        config_path = Path(__file__).parent / '.model_schedules.json'
        if not config_path.exists():
            print("[模型切换] 错误: .model_schedules.json 不存在")
            self._valid = False
            return

        self._valid = True
        with open(config_path) as f:
            self.config = json.load(f)

        settings_path_raw = self.config.get('settings_path', '~/.claude/settings.json')
        self.settings_path = Path(os.path.expanduser(settings_path_raw))
        self.default_env = self.config['default']
        self.schedules = self.config.get('schedules', [])
        self.check_interval = self.config.get('check_interval', 60)
        self.fallback_models = self.config.get('fallback_models', [])
        self.current_name = None

    def _parse_time(self, t):
        h, m = map(int, t.split(':'))
        return h * 60 + m

    def _get_schedule_env(self):
        now = time.localtime()
        now_min = now.tm_hour * 60 + now.tm_min
        for s in self.schedules:
            start = self._parse_time(s['start'])
            end = self._parse_time(s['end'])
            if start <= end:
                if start <= now_min < end:
                    return s['env'], s['name']
            else:  # crosses midnight
                if now_min >= start or now_min < end:
                    return s['env'], s['name']
        return self.default_env, '默认'

    def _is_claude_running(self):
        """检测 Claude 进程是否存在"""
        try:
            r = subprocess.run(['pgrep', '-f', 'claude'],
                             capture_output=True, text=True, timeout=5)
            pids = r.stdout.strip().split('\n') if r.stdout.strip() else []
            my_pid = str(os.getpid())
            return any(p for p in pids if p and p != my_pid)
        except Exception:
            return False

    def _is_claude_idle(self):
        """通过 tmux 屏幕判断 Claude 是否在等待用户输入（未调用模型）"""
        try:
            r = subprocess.run(['tmux', 'capture-pane', '-t', self.session_name, '-p', '-J'],
                             capture_output=True, text=True, timeout=1)
            lines = [l for l in r.stdout.split('\n') if l.strip()]
            if not lines:
                return True
            last_lines = '\n'.join(lines[-5:])
            # 确认提示屏不算空闲（Claude 正在执行任务，只是暂停等权限）
            confirm_keywords = ['requires approval', 'do you want', 'proceed', 'allow']
            if any(kw in last_lines.lower() for kw in confirm_keywords):
                return False
            # 输入提示符 ❯ 表示 Claude 在等用户输入，模型空闲
            return '❯' in last_lines
        except Exception:
            return True

    def _read_settings(self):
        try:
            with open(self.settings_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"[模型切换] 读取 settings.json 失败: {e}")
            return None

    def _write_settings(self, data):
        bak = self.settings_path.with_suffix('.json.bak')
        try:
            shutil.copy2(self.settings_path, bak)
        except Exception:
            pass
        with open(self.settings_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')

    def _do_switch(self, env, name):
        settings = self._read_settings()
        if not settings:
            return False
        if settings.get('env') == env:
            self.current_name = name
            return False
        settings['env'] = env
        self._write_settings(settings)
        self.current_name = name
        return True

    def run(self):
        if not self._valid:
            return
        print(f"[模型切换] 启动 | 检查间隔: {self.check_interval}s | 配置: {len(self.schedules)}个时段")
        for s in self.schedules:
            print(f"  {s['name']}: {s['start']} - {s['end']}")
        print(f"  默认: 其他时间")

        while not self.stop_event.is_set():
            # 没有 Claude 进程，一起停
            if not self._is_claude_running():
                ts = time.strftime('%H:%M:%S')
                print(f"[{ts}] [模型切换] Claude 进程不存在，退出")
                self.stop_event.set()
                break

            target_env, target_name = self._get_schedule_env()

            # fallback 激活时不覆盖
            if self.fallback_active_file.exists():
                ts = time.strftime('%H:%M:%S')
                fb_name = self.fallback_active_file.read_text().strip()
                print(f"[{ts}] [模型切换] fallback 已激活 ({fb_name})，跳过定时切换")
                self.current_name = f"fallback:{fb_name}"
                self.stop_event.wait(self.check_interval)
                continue

            if target_name != self.current_name:
                if self._is_claude_idle():
                    ts = time.strftime('%H:%M:%S')
                    if self._do_switch(target_env, target_name):
                        print(f"[{ts}] [模型切换] 已切换到: {target_name}")
                    else:
                        self.current_name = target_name
                        print(f"[{ts}] [模型切换] 当前已是: {target_name}")
                else:
                    ts = time.strftime('%H:%M:%S')
                    print(f"[{ts}] [模型切换] Claude 正在调用模型，等待... (目标: {target_name})")

            self.stop_event.wait(self.check_interval)

    def check_and_switch(self, dry_run=False):
        """单次检查并切换，用于 hook 模式（hook 被调用时 Claude 必然不在调模型）

        Args:
            dry_run: True 时只检测不写入 settings.json（避免触发 Claude Code 重载导致滚屏）
        """
        if not self._valid:
            return
        if self.fallback_active_file.exists():
            print("[模型切换] fallback 已激活，跳过", file=sys.stderr)
            return
        target_env, target_name = self._get_schedule_env()
        # 直接读文件比对，不依赖 self.current_name（hook 每次是新实例）
        current_model = None
        try:
            with open(self.settings_path) as f:
                current_model = json.load(f).get('env', {}).get('ANTHROPIC_DEFAULT_OPUS_MODEL')
        except Exception:
            pass
        if target_env.get('ANTHROPIC_DEFAULT_OPUS_MODEL') == current_model:
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [模型切换] {target_name}（已是目标）", file=sys.stderr)
            return
        if dry_run:
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [模型切换] 需要切换到 {target_name}（dry_run，不写入）", file=sys.stderr)
            return
        if self._do_switch(target_env, target_name):
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [模型切换] 已切换到: {target_name}", file=sys.stderr)
        else:
            ts = time.strftime('%H:%M:%S')
            print(f"[{ts}] [模型切换] 当前已是: {target_name}", file=sys.stderr)


def do_setup(args):
    """
    根据参数配置 ~/.claude/settings.json 的 hooks

    --full --setup: 安装 3 个独立 hook
      - PermissionRequest → python3 script --full（Hook + AI + 全部允许）
      - StopFailure      → python3 script --fallback（连续失败切换备用模型）
      - ModelSwitcher    → python3 script --model-switch（定时切换模型，独立进程）

    --hook --setup: 只安装 PermissionRequest hook
    --fallback --setup: 只安装 StopFailure hook
    """
    script = str(Path(__file__).resolve())

    if not args.full and not args.hook and not args.fallback:
        print("错误: --setup 需要配合 --full、--hook 或 --fallback 使用")
        sys.exit(1)

    # 加载 settings_path
    config_path = Path(__file__).parent / '.model_schedules.json'
    if config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        settings_path = Path(os.path.expanduser(cfg.get('settings_path', '~/.claude/settings.json')))
    else:
        settings_path = Path.home() / '.claude' / 'settings.json'

    # 读取现有 settings（保留 env、plugins 等其他配置）
    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)
    else:
        settings = {}

    hooks = settings.get('hooks', {})

    # --full --setup：安装 2 个 hook
    if args.full:
        # 1. PermissionRequest: hook + ai + allow-all
        cmd_full = f"python3 {script} --full"
        hooks["PermissionRequest"] = [{"hooks": [{"type": "command", "command": cmd_full}]}]
        print(f"[Setup] PermissionRequest → {cmd_full}")

        # 2. StopFailure: fallback + model-switch（StopFailure 触发后顺便检查模型时间表）
        cmd_fallback = f"python3 {script} --fallback --model-switch"
        hooks["StopFailure"] = [{"hooks": [{"type": "command", "command": cmd_fallback}]}]
        print(f"[Setup] StopFailure → {cmd_fallback}")

        # 注意：--tmux --model-switch 会启动后台循环线程，定时检查模型切换
        print(f"[Setup] 如需 --tmux 模式自动切换，另行运行: python3 {script} --tmux --model-switch")

    # --hook --setup：只安装 PermissionRequest
    elif args.hook:
        parts = ["python3", script, "--hook"]
        if args.ai:
            parts.append("--ai")
        if args.allow_all:
            parts.append("--allow-all")
        cmd = " ".join(parts)
        hooks["PermissionRequest"] = [{"hooks": [{"type": "command", "command": cmd}]}]
        print(f"[Setup] PermissionRequest → {cmd}")

    # --fallback --setup：只安装 StopFailure
    if args.fallback and not args.full:
        cmd = f"python3 {script} --fallback"
        hooks["StopFailure"] = [{"hooks": [{"type": "command", "command": cmd}]}]
        print(f"[Setup] StopFailure → {cmd}")

    # 写回
    settings['hooks'] = hooks
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, 'w') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"[Setup] 已写入 {settings_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智能确认器 - 自动响应 Claude Code 权限确认提示")
    parser.add_argument("session", nargs="?", default="claude", help="tmux 会话名")
    parser.add_argument("--tmux", action="store_true", help="tmux 轮询模式")
    parser.add_argument("--hook", action="store_true", help="PermissionRequest Hook 模式")
    parser.add_argument("--ai", action="store_true", help="AI 兜底")
    parser.add_argument("--allow-all", action="store_true", help="Hook 模式下全部允许（仍拦截危险命令）")
    parser.add_argument("--model-switch", action="store_true", help="模型时间表检查（单独使用或配合 --fallback 时单次检查，配合 --tmux 时循环）")
    parser.add_argument("--full", action="store_true", help="等价于 --hook --ai --allow-all（Hook + AI 兜底 + 全部允许）")
    parser.add_argument("--fallback", action="store_true", help="StopFailure 连续失败后自动切换备用模型")
    parser.add_argument("--fallback-threshold", type=int, default=3, help="连续失败多少次后切换（默认3）")
    parser.add_argument("--fallback-reset", action="store_true", help="重置 fallback 失败计数和激活状态")
    parser.add_argument("--setup", action="store_true", help="根据当前参数配置 ~/.claude/settings.json 的 hooks")
    args = parser.parse_args()

    if args.setup:
        do_setup(args)
        sys.exit(0)

    if args.fallback_reset:
        # 重置 fallback 状态（可独立使用，也可配合 --fallback）
        FallbackHandler(threshold=args.fallback_threshold).reset()
        sys.exit(0)

    if args.fallback:
        # StopFailure hook 独立模式
        handler = FallbackHandler(threshold=args.fallback_threshold)
        raw = sys.stdin.read()
        if raw.strip():
            try:
                input_data = json.loads(raw)
                error_type = input_data.get('error', 'unknown')
            except json.JSONDecodeError:
                error_type = 'unknown'
            handler.handle_stop_failure(error_type)
        else:
            print("[Fallback] 从 stdin 读取 StopFailure JSON，由 Claude Code 自动调用。", file=sys.stderr)
            print("手动测试:", file=sys.stderr)
            print('  echo \'{"error":"rate_limit"}\' | python3 smart_confirmer.py --fallback', file=sys.stderr)
            sys.exit(1)

        # --model-switch 附带：StopFailure 触发后顺便检查模型时间表
        if args.model_switch:
            ModelSwitcher(args.session, threading.Event()).check_and_switch()
    elif args.hook or args.full:
        HookHandler(use_ai=args.ai or args.full, allow_all=args.allow_all or args.full).run_hook()
    elif args.tmux:
        confirmer = FixConfirmer(args.session, use_ai=args.ai)
        if args.model_switch:
            ModelSwitcher(args.session, confirmer.stop_event).start()
        confirmer.run()
    elif args.model_switch:
        # hook 上下文（stdin 有数据）：单次检查后 exit
        # 独立进程（stdin 为空）：循环运行
        raw = sys.stdin.read()
        if raw.strip():
            ModelSwitcher(args.session, threading.Event()).check_and_switch()
        else:
            stop_event = threading.Event()
            signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
            signal.signal(signal.SIGINT, lambda *_: stop_event.set())
            ModelSwitcher(args.session, stop_event).run()
    else:
        parser.print_help()
        print("\n错误: 请指定运行模式 (--tmux, --hook, 或 --model-switch)")
        sys.exit(1)
