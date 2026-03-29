#!/usr/bin/env python3
"""
智能确认记录系统
记录确认历史，避免重复确认相同内容
"""

import time
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import difflib

@dataclass
class ConfirmRecord:
    """确认记录"""
    timestamp: float
    confirm_type: str
    content_hash: str
    content_preview: str
    action_taken: str
    session_name: str

class ConfirmHistory:
    """确认历史管理器"""
    
    def __init__(self, history_file: str = "/tmp/claude_confirm_history.json"):
        self.history_file = history_file
        self.records: List[ConfirmRecord] = []
        self.load_history()
    
    def load_history(self):
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [ConfirmRecord(**r) for r in data]
            except Exception as e:
                print(f"[警告] 无法加载历史记录: {e}")
                self.records = []
    
    def save_history(self):
        """保存历史记录"""
        try:
            data = [asdict(r) for r in self.records]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[警告] 无法保存历史记录: {e}")
    
    def add_record(self, confirm_type: str, content: str, action: str, session: str):
        """添加确认记录"""
        # 生成内容哈希
        content_hash = self.hash_content(content)
        
        # 内容预览（最后 200 字符）
        content_preview = content[-200:] if len(content) > 200 else content
        
        # 创建记录
        record = ConfirmRecord(
            timestamp=time.time(),
            confirm_type=confirm_type,
            content_hash=content_hash,
            content_preview=content_preview,
            action_taken=action,
            session_name=session
        )
        
        self.records.append(record)
        
        # 只保留最近 100 条记录
        if len(self.records) > 100:
            self.records = self.records[-100:]
        
        self.save_history()
    
    def hash_content(self, content: str) -> str:
        """生成内容哈希"""
        # 标准化内容：去除空格、转义字符等
        normalized = content.strip()
        normalized = ' '.join(normalized.split())
        
        # 使用 SHA256 哈希
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def should_confirm(self, confirm_type: str, content: str, timeout: int = 300) -> tuple:
        """
        判断是否应该确认
        返回: (should_confirm: bool, reason: str)
        """
        now = time.time()
        content_hash = self.hash_content(content)
        
        # 检查完全相同的内容
        for record in reversed(self.records):
            # 时间检查
            if now - record.timestamp > timeout:
                break
            
            # 类型检查
            if record.confirm_type != confirm_type:
                continue
            
            # 完全相同的内容
            if record.content_hash == content_hash:
                elapsed = int(now - record.timestamp)
                return (False, f"相同内容已在 {elapsed} 秒前确认过")
        
        # 检查相似内容（使用字符串相似度）
        content_preview = content[-200:] if len(content) > 200 else content
        
        for record in reversed(self.records):
            if now - record.timestamp > timeout:
                break
            
            if record.confirm_type != confirm_type:
                continue
            
            # 计算相似度
            similarity = difflib.SequenceMatcher(
                None,
                record.content_preview,
                content_preview
            ).ratio()
            
            if similarity > 0.85:  # 85% 相似度
                elapsed = int(now - record.timestamp)
                return (False, f"相似内容({similarity:.1%})已在 {elapsed} 秒前确认过")
        
        return (True, "首次确认或内容已变化")
    
    def get_recent_confirms(self, count: int = 10) -> List[ConfirmRecord]:
        """获取最近的确认记录"""
        return reversed(self.records[-count:])
    
    def show_stats(self):
        """显示统计信息"""
        if not self.records:
            print("暂无确认记录")
            return
        
        print("\n" + "=" * 60)
        print("确认历史统计")
        print("=" * 60)
        
        # 按类型统计
        type_counts = {}
        for record in self.records:
            type_counts[record.confirm_type] = type_counts.get(record.confirm_type, 0) + 1
        
        print("\n确认类型统计:")
        for confirm_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {confirm_type}: {count} 次")
        
        print(f"\n总确认次数: {len(self.records)}")
        
        # 最近的确认
        print("\n最近 5 次确认:")
        for i, record in enumerate(self.get_recent_confirms(5), 1):
            elapsed = int(time.time() - record.timestamp)
            print(f"  {i}. [{record.confirm_type}] {elapsed} 秒前")
            print(f"     操作: {record.action_taken}")
            print(f"     内容: {record.content_preview[:60]}...")
            print()
        
        print("=" * 60)


# 使用示例
if __name__ == "__main__":
    history = ConfirmHistory("/tmp/test_confirm_history.json")
    
    # 测试添加记录
    history.add_record(
        confirm_type="allow_directory",
        content="Do you want to proceed?\n ❯ 1. Yes\n   2. Yes, allow access\n",
        action="发送按键: 2 + Enter",
        session="claude"
    )
    
    # 测试是否应该确认
    should_confirm, reason = history.should_confirm(
        confirm_type="allow_directory",
        content="Do you want to proceed?\n ❯ 1. Yes\n   2. Yes, allow access\n",
        timeout=300
    )
    
    print(f"应该确认: {should_confirm}")
    print(f"原因: {reason}")
    
    # 显示统计
    history.show_stats()
