# -*- coding: utf-8 -*-
# @Time : 2025-12-24
# @Author : Yolen
# -----------------------------------------------
# async_http_client.py
import asyncio
import logging
from functools import wraps
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class AsyncHTTPClientPool:
    """简化的异步HTTP客户端池"""

    _lock: asyncio.Lock = aiohttp.Lock()
    _session: Optional[aiohttp.ClientSession] = None
    _connector: Optional[aiohttp.TCPConnector] = None

    @classmethod
    async def _init_session(cls):
        if cls._session is not None and not cls._session.closed:
            return
        """初始化HTTP会话（延迟懒加载）"""
        async with cls._lock:
            if cls._session is not None and not cls._session.closed:
                return
            # 为3000台设备优化连接池配置
            cls._connector = aiohttp.TCPConnector(
                limit=500,  # 总连接数，根据系统资源调整
                limit_per_host=0,  # 不限制单个主机连接数，让连接池自由分配
                enable_cleanup_closed=True,
                ttl_dns_cache=600,  # DNS缓存10分钟
                ssl=False
            )

            timeout = aiohttp.ClientTimeout(
                total=2 * 60,  # 总超时秒
                connect=30,  # 连接超时秒
                sock_read=30  # 读取超时秒
            )

            cls._session = aiohttp.ClientSession(
                connector=cls._connector,
                timeout=timeout,
            )
            logger.info("初始化HTTP客户端会话完成")

    @classmethod
    def ensure_session(cls, func):
        """装饰器：确保会话已初始化"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if cls._session is None or cls._session.closed:
                await cls._init_session()
            return await func(*args, **kwargs)

        return wrapper

    @classmethod
    async def get_session(cls) -> Optional[aiohttp.ClientSession]:
        if cls._session is not None and not cls._session.closed:
            return cls._session
        await cls._init_session()
        return cls._session

    @classmethod
    @ensure_session
    async def request(cls, method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """执行HTTP请求"""
        session = await cls.get_session()

        # 对于周期性任务，使用简单的重试机制
        try:
            async with session.request(method, url, **kwargs) as response:
                return response
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f'请求异常：error-{e}')
        except Exception as e:
            logger.error(f'未知异常：error-{e}')
        return None

    @classmethod
    async def get(cls, url: str, **kwargs):
        """GET请求快捷方法"""
        return await cls.request('GET', url, **kwargs)

    @classmethod
    async def post(cls, url: str, **kwargs):
        """POST请求快捷方法"""
        return await cls.request('POST', url, **kwargs)

    @classmethod
    async def put(cls, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """PUT请求快捷方法"""
        return await cls.request('PUT', url, **kwargs)

    @classmethod
    async def delete(cls, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """DELETE请求快捷方法"""
        return await cls.request('DELETE', url, **kwargs)

    @classmethod
    async def patch(cls, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """PATCH请求快捷方法"""
        return await cls.request('PATCH', url, **kwargs)

    @classmethod
    async def close(cls):
        """关闭连接池"""
        if cls._session is None or cls._session.closed:
            return
        async with cls._lock:
            if cls._session is None or cls._session.closed:
                return
            await cls._session.close()
            cls._session = None
            cls._connector = None
        logger.info("关闭HTTP客户端会话完成")
