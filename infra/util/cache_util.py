# -*- coding: utf-8 -*-
# @Time : 2025-12-27
# @Author : Yolen
# -----------------------------------------------
import time
from typing import Optional, Dict


class SessionCache:
    """简化版会话缓存（仅缓存登录信息）"""

    def __init__(self, ttl_seconds: int = 600):  # 会话缓存10分钟
        self.cache = {}
        self.ttl = ttl_seconds

    def get(self, device_ip: str) -> Optional[Dict]:
        """获取缓存会话"""
        entry = self.cache.get(device_ip)
        if entry and time.time() - entry['timestamp'] < self.ttl:
            return entry['data']
        return None

    def set(self, device_ip: str, data: Dict):
        """设置缓存会话"""
        self.cache[device_ip] = {
            'data': data,
            'timestamp': time.time()
        }

    def clear_expired(self):
        """清理过期会话（可选，由外部调用）"""
        now = time.time()
        expired_keys = [
            k for k, v in self.cache.items()
            if now - v['timestamp'] >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
