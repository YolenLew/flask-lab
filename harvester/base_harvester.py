# -*- coding: utf-8 -*-
# @Time : 2026-01-01
# @Author : Yolen
# -----------------------------------------------
import asyncio
import time
from typing import Dict, Any, Optional, List

from config.async_client_config import AsyncHTTPClientPool, logger


class HarvesterBase:
    """简化版采集器基类"""

    def __init__(self, data: Dict[str, Any]):
        self.data = data or {}
        self.username = self.data.get('username')
        self.password = self.data.get('password')
        self.ip = self.data.get('ip')
        self.uri = f"https://{self.ip}"

        # 共享的HTTP客户端池
        self.http_pool = AsyncHTTPClientPool()

        # 采集数据容器
        self.collect_data: Dict[str, Any] = {}
        # 格式化指标数据的容器
        self.monitor_info: Dict[str, List] = {}
        # 错误信息容器
        self.error_data: Dict[str, list] = {}

        # 认证信息
        self.auth_headers = {}

        # 默认组件接口
        self.default_urls = {
            "cpu": {"url": "/api/chassis/cpu", "method": "GET", "enable": True},
            "memory": {"url": "/api/chassis/memory", "method": "GET", "enable": True},
            "disk": {"url": "/api/chassis/disk", "method": "GET", "enable": True},
            "adapter": {"url": "/api/chassis/adapter", "method": "GET", "enable": True},
            "pcie": {"url": "/api/chassis/pcie", "method": "GET", "enable": True},
            "fan": {"url": "/api/chassis/fan", "method": "GET", "enable": True},
            "event": {"url": "/api/chassis/event", "method": "GET", "enable": True},
        }

    async def create_session(self) -> bool:
        """创建BMC会话（需子类实现）"""
        raise NotImplementedError()

    async def delete_session(self) -> bool:
        """删除BMC会话(建议实现，否则可能导致会话数超限制无法登录)"""
        pass

    async def _do_login(self) -> bool:
        """执行登录逻辑"""
        if self.auth_headers:
            return True
        if await self.create_session():
            return True
        return False

    async def _fetch_single(self, component: str, url: str):
        """采集单个组件"""
        # 判断是否已采集，避免重复采集
        if component in self.collect_data:
            return self.collect_data[component]
        full_url = f"{self.uri}{url}"

        try:
            response = await self.http_pool.get(
                url=full_url,
                headers=self.auth_headers,
                ssl=False
            )

            if response.status == 200:
                data = await response.json()
                if component not in self.collect_data:
                    self.collect_data[component] = []
                self.collect_data[component].append(data)
                logger.info(f"设备 {self.ip} 采集 {component} 成功")
                return self.collect_data[component]
            elif response.status == 401:
                # 认证失效，清除缓存并重新登录
                if await self._do_login():
                    # 重试一次
                    response = await self.http_pool.get(
                        full_url,
                        headers=self.auth_headers,
                        ssl=False
                    )
                    if response.status == 200:
                        data = await response.json()
                        if component not in self.collect_data:
                            self.collect_data[component] = []
                        self.collect_data[component].append(data)
                    else:
                        self._record_error(component, f"HTTP {response.status}")
                else:
                    self._record_error(component, "重新登录失败")
            else:
                self._record_error(component, f"HTTP {response.status}")
        except Exception as e:
            self._record_error(component, str(e))
        return []

    def _record_error(self, component: str, error_msg: str):
        """记录错误信息"""
        if component not in self.error_data:
            self.error_data[component] = []
        self.error_data[component].append({
            "error": error_msg,
            "component": component,
            "device_ip": self.ip,
            "timestamp": time.time()
        })

    async def fetch_info(self, target_part: Optional[List[str]] = None) -> Dict[str, list]:
        """采集所有部件信息"""
        # 清空上次数据
        self.collect_data = {}

        # 登录验证
        if not await self._do_login():
            raise ConnectionError(f"设备 {self.ip} 登录失败")

        # 确定要采集的组件
        components_to_fetch = {}
        if target_part:
            # 只采集指定的部件
            for component in target_part:
                if component in self.default_urls:
                    # 优先使用data中指定的URL
                    url_info = self.data.get(component, self.default_urls[component])
                    components_to_fetch[component] = url_info
                else:
                    logger.warning(f"设备 {self.ip} 不支持采集部件: {component}")
                    self._record_error(component, f"不支持的部件: {component}")
        else:
            # 采集所有部件
            components_to_fetch = {part: url_info for part, url_info in self.default_urls.items()}

        # 并发采集所有组件（一个设备内的组件并发采集）
        tasks = [
            self._fetch_single(component, url_info.get('url'))
            for component, url_info in components_to_fetch.items()
        ]

        # 一个设备最多同时发起3个请求（避免占用过多连接）
        semaphore = asyncio.Semaphore(6)

        async def limited_task(task):
            async with semaphore:
                return await task

        limited_tasks = [limited_task(task) for task in tasks]
        await asyncio.gather(*limited_tasks, return_exceptions=True)

        return self.collect_data

    async def insert_monitor_cpu(self):
        """CPU指标信息"""
        self.fetch_info(target_part=["cpu"])
