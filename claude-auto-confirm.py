#!/usr/bin/env python3
"""
Claude Code 自动确认器 (适配 Claude 2.1.86)
监控 tmux 会话中的 Claude Code，自动检测并确认各种提示

使用方法:
  python3 claude-auto-confirm.py [会话名]

示例:
  python3 claude-auto-confirm.py          # 默认监控 'claude' 会话
  python3 claude-auto-confirm.py mysession # 监控指定会话
"""

import os
import sys
import re
import time
import subprocess
from typing import Optional, List, Tuple
from dataclasses import dataclass

# 导入确认历史管理器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from confirm_history import ConfirmHistory

# 默认配置
DEFAULT_SESSION = "claude"
CHECK_INTERVAL = 0.3  # 检查间隔（秒）
CONFIRM_DELAY = 0.2   # 确认延迟（秒）
SESSION_TIMEOUT = 0  # 会话超时（秒），0 表示永不超时

@dataclass
class ConfirmPattern:
    """确认模式"""
    name: str
    pattern: str
    action: str  # 'yes', 'yes_all', 'no', 'custom'
    custom_key: str = ""  # 自定义按键
    priority: int = 0  # 优先级，越高越优先

class ClaudeConfirmer:
    def __init__(self, session_name: str = DEFAULT_SESSION):
        self.session_name = session_name
        self.patterns: List[ConfirmPattern] = []
        self.last_confirmed = {}  # 记录上次确认的时间，防止重复确认
        self.running = True
        self.start_time = time.time()
        
        # 初始化确认历史管理器
        history_file = f"/tmp/claude_confirm_{session_name}.json"
        self.history = ConfirmHistory(history_file)
        
        # Claude 2.1.86 的确认提示模式
        # 更新：支持 "always allow access to 123/ from this project" 格式
        self.confirm_patterns = [
            # 最高优先级：永久允许目录访问
            {
                'name': 'always_allow_directory',
                'patterns': [
                    r'Yes,\s+and\s+always\s+allow\s+access\s+to\s+\S+\s+from\s+this\s+project',
                    r'always\s+allow\s+access\s+to',
                    r'and\s+always\s+allow',
                ],
                'action': 'yes_all',
                'priority': 110
            },
            # 高优先级：读取文件确认（允许目录访问）
            {
                'name': 'allow_directory',
                'patterns': [
                    r'Yes,\s+allow\s+reading\s+from\s+\S+\s+during\s+this\s+session',
                    r'allow\s+reading\s+from',
                ],
                'action': 'yes_all',
                'priority': 100
            },
            # 高优先级：编辑确认（允许全部编辑）
            {
                'name': 'allow_all_edits',
                'patterns': [
                    r'Yes,\s+allow\s+all\s+edits\s+for\s+this\s+session',
                    r'allow\s+all\s+edits',
                    r'Yes,\s+allow\s+editing\s+files\s+in\s+',
                ],
                'action': 'yes_all',
                'priority': 90
            },
            # 继续操作确认
            {
                'name': 'proceed',
                'patterns': [
                    r'Do\s+you\s+want\s+to\s+proceed\?',
                    r'Proceed\?',
                    r'Continue\?',
                ],
                'action': 'yes',
                'priority': 80
            },
            # 运行命令确认
            {
                'name': 'run_command',
                'patterns': [
                    r'Run\s+(bash|command|script)',
                    r'Execute\s+command',
                ],
                'action': 'yes',
                'priority': 70
            },
            # 通用 Yes/No 确认
            {
                'name': 'generic_yes',
                'patterns': [
                    r'❯\s*1\.\s*Yes',
                    r'\[1\]\s*Yes',
                    r'Create directory',
                    r'mkdir',
                ],
                'action': 'yes',
                'priority': 50
            },
            # 菜单选择（通用）
            {
                'name': 'menu_select',
                'patterns': [
                    r'❯\s*\d+\.\s*\w+',
                    r'\[\d+\]\s*\w+',
                ],
                'action': 'yes',
                'priority': 40
            },
        ]
        
        # 编译正则表达式
        self.compiled_patterns = []
        for pattern_group in self.confirm_patterns:
            compiled = {
                'name': pattern_group['name'],
                'action': pattern_group['action'],
                'priority': pattern_group['priority'],
                'regexes': [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in pattern_group['patterns']]
            }
            self.compiled_patterns.append(compiled)
    
    def setup_patterns(self):
        """设置默认模式（保留兼容性）"""
        pass  # 已经在 __init__ 中设置
    
    def capture_pane(self) -> str:
        """捕获 tmux pane 内容"""
        try:
            result = subprocess.run(
                ['tmux', 'capture-pane', '-t', self.session_name, '-p'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout
            return ""
        except Exception as e:
            print(f"[错误] 无法捕获 tmux 内容: {e}")
            return ""
    
    def detect_confirm(self, content: str) -> Optional[Tuple[str, str]]:
        """检测确认提示，返回 (类型, 建议操作)"""
        if not content:
            return None
        
        # 只检查最后 3000 字符
        recent_content = content[-3000:]
        
        # 简化检测：直接检查是否包含确认提示的特征
        # 必须同时包含：
        # 1. 确认问题文本
        # 2. 数字选项
        
        has_question = False
        has_options = False
        
        # 检查确认问题
        question_patterns = [
            r'Do you want to proceed',
            r'Proceed\?',
            r'Continue\?',
            r'always allow access',
            r'allow all edits',
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, recent_content, re.IGNORECASE):
                has_question = True
                break
        
        # 检查选项
        # 放宽选项检测：只要有数字选项就行，不一定需要 "Yes" 文字
        if re.search(r'❯\s*\d+\.', recent_content) or re.search(r'\d+\.\s*Yes', recent_content):
            has_options = True
        
        # 如果都有，检测为确认提示
        if has_question and has_options:
            # 检查是否有 "always allow" 或 "allow all"
            if re.search(r'always allow access|allow all edits', recent_content, re.IGNORECASE):
                return ('allow_all', '2')
            else:
                return ('yes', '1')
        
        # 按优先级检查模式（备用）
        best_match = None
        best_priority = -1
        
        for pattern_group in self.compiled_patterns:
            if pattern_group['priority'] <= best_priority:
                continue
            
            for regex in pattern_group['regexes']:
                match = regex.search(recent_content)
                if match:
                    if pattern_group['priority'] > best_priority:
                        best_match = (pattern_group['name'], pattern_group['action'])
                        best_priority = pattern_group['priority']
                    break
        
        if best_match:
            confirm_type, action = best_match
            if action == 'yes_all':
                return (confirm_type, '2')
            elif action == 'yes':
                return (confirm_type, '1')
            elif action == 'no':
                return (confirm_type, '3')
        
        return None
    
    def send_confirm(self, key: str) -> bool:
        """发送确认按键"""
        try:
            # 发送按键前先检查是否在命令行中
            # 如果在命令行（显示提示符），不要发送按键
            content = self.capture_pane()
            if content:
                # 检查最后几行是否是命令行提示符
                last_lines = content[-200:]
                # 如果包含典型的 bash/zsh 提示符，说明在命令行，不应该确认
                if re.search(r'[\[\(][^\]\)]+[\]\)].*[\$#%]\s*$', last_lines):
                    # 在命令行，不发送确认
                    return False
            
            # 发送数字键
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, key],
                check=True,
                timeout=2
            )
            
            # 等待一小段时间
            time.sleep(0.1)
            
            # 发送回车键确认
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.session_name, 'Enter'],
                check=True,
                timeout=2
            )
            
            print(f"[确认] 发送按键: {key} + Enter")
            return True
        except Exception as e:
            print(f"[错误] 无法发送按键: {e}")
            return False
    
    def should_confirm(self, confirm_type: str, content: str) -> tuple:
        """
        判断是否应该确认（防止重复确认）
        返回: (should_confirm: bool, reason: str)
        """
        # 使用智能历史系统检查
        should_confirm, reason = self.history.should_confirm(
            confirm_type=confirm_type,
            content=content,
            timeout=300  # 5 分钟
        )
        
        if not should_confirm:
            return (False, reason)
        
        # 额外检查：如果内容包含之前发送的按键错误，跳过
        if '-bash:' in content and '未找到命令' in content:
            return (False, "检测到命令执行错误，暂停确认")
        
        # 额外检查：如果内容包含重复的数字，说明已经发送过了
        lines = content.split('\n')
        number_count = 0
        for line in lines[-20:]:
            if line.strip().isdigit() and len(line.strip()) <= 2:
                number_count += 1
        
        if number_count > 5:
            return (False, f"检测到 {number_count} 个重复数字，可能已确认")
        
        return (True, "首次确认或内容已变化")
    
    def mark_confirmed(self, confirm_type: str, content: str):
        """标记已确认"""
        now = time.time()
        self.last_confirmed[confirm_type] = now
        
        content_hash = hash(content[-1000:])
        hash_key = f"{confirm_type}_{content_hash}"
        self.last_confirmed[hash_key] = now
    
    def check_session_timeout(self):
        """检查会话是否超时"""
        if SESSION_TIMEOUT > 0:
            elapsed = time.time() - self.start_time
            if elapsed > SESSION_TIMEOUT:
                print(f"[超时] 会话运行超过 {SESSION_TIMEOUT} 秒，自动退出")
                self.running = False
    
    def monitor_loop(self):
        """监控循环"""
        print(f"[启动] 监控 tmux 会话: {self.session_name}")
        print(f"[信息] Claude Code 2.1.86 适配版本")
        print(f"[信息] 按 Ctrl+C 停止监控")
        if SESSION_TIMEOUT > 0:
            print(f"[信息] 会话超时: {SESSION_TIMEOUT} 秒")
        else:
            print(f"[信息] 会话超时: 已禁用（持续运行）")
        print("-" * 50)
        
        no_confirm_count = 0
        max_no_confirm = 30  # 连续 30 次没有确认提示后减少检查频率
        
        try:
            check_count = 0
            while self.running:
                check_count += 1
                
                # 每10次检查输出一次状态
                if check_count % 10 == 0:
                    print(f"[轮询] 第 {check_count} 次检查...", flush=True)
                
                # 检查超时
                self.check_session_timeout()
                if not self.running:
                    break
                
                # 捕获内容
                content = self.capture_pane()
                
                if content:
                    # 每20次检查显示一次内容预览
                    if check_count % 20 == 0:
                        print(f"[内容预览] ...{content[-100:]}", flush=True)
                    
                    # 检测确认提示
                    result = self.detect_confirm(content)
                    
                    if result:
                        confirm_type, key = result
                        
                        # 判断是否应该确认
                        should_confirm, reason = self.should_confirm(confirm_type, content)
                        
                        if should_confirm:
                            print(f"\n[检测] 确认类型: {confirm_type}")
                            print(f"[原因] {reason}")
                            print(f"[内容预览] ...{content[-150:].strip()}")
                            
                            # 等待一下让 UI 稳定
                            time.sleep(CONFIRM_DELAY)
                            
                            # 发送确认
                            if self.send_confirm(key):
                                # 记录到历史
                                self.history.add_record(
                                    confirm_type=confirm_type,
                                    content=content,
                                    action=f"发送按键: {key} + Enter",
                                    session=self.session_name
                                )
                                
                                self.mark_confirmed(confirm_type, content)
                                no_confirm_count = 0
                                
                                # 发送后立即标记，防止重复
                                self.last_confirmed[f"{confirm_type}_last"] = time.time()
                                
                                # 等待更长时间，避免重复
                                time.sleep(2)
                        else:
                            print(f"\n[跳过] 确认类型: {confirm_type}")
                            print(f"[原因] {reason}")
                            no_confirm_count += 1
                    else:
                        no_confirm_count += 1
                else:
                    no_confirm_count += 1
                
                # 动态调整检查频率
                if no_confirm_count > max_no_confirm:
                    time.sleep(CHECK_INTERVAL * 3)  # 降低频率
                else:
                    time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print(f"\n\n[停止] 监控已停止")
            print(f"[统计] 运行时长: {int(time.time() - self.start_time)} 秒")
            
            # 显示确认历史统计
            self.history.show_stats()
        except Exception as e:
            print(f"\n[错误] {e}")
    
    def stop(self):
        """停止监控"""
        self.running = False

def main():
    # 获取会话名
    session_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SESSION
    
    # 创建确认器
    confirmer = ClaudeConfirmer(session_name)
    confirmer.setup_patterns()
    
    # 开始监控
    confirmer.monitor_loop()

if __name__ == "__main__":
    main()
