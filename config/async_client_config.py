# -*- coding: utf-8 -*-
# @Time : 2025-12-24
# @Author : Yolen
# -----------------------------------------------
# async_http_client.py
import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class AsyncHTTPClientPool:
    """简化的异步HTTP客户端池"""

    _instance = None
    _session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._connector = None
            self._initialized = True

    async def get_session(self) -> aiohttp.ClientSession:
        """获取共享的客户端会话"""
        if self._session is None or self._session.closed:
            # 为3000台设备优化连接池配置
            self._connector = aiohttp.TCPConnector(
                limit=500,  # 总连接数，根据系统资源调整
                limit_per_host=0,  # 不限制单个主机连接数，让连接池自由分配
                enable_cleanup_closed=True,
                ttl_dns_cache=600,  # DNS缓存10分钟
                ssl=False
            )

            timeout = aiohttp.ClientTimeout(
                total=80,  # 总超时30秒
                connect=30,  # 连接超时10秒
                sock_read=30  # 读取超时25秒
            )

            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
            )
            logger.info("初始化HTTP客户端会话完成")

        return self._session

    async def request(self, method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """执行HTTP请求"""
        session = await self.get_session()

        # 对于周期性任务，使用简单的重试机制
        try:
            async with session.request(method, url, **kwargs) as response:
                return response
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f'请求异常：error-{e}')
        return None

    async def get(self, url: str, **kwargs):
        """GET请求快捷方法"""
        return await self.request('GET', url, **kwargs)

    async def post(self, url: str, **kwargs):
        """POST请求快捷方法"""
        return await self.request('POST', url, **kwargs)

    async def close(self):
        """关闭连接池"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.info("关闭HTTP客户端会话")

