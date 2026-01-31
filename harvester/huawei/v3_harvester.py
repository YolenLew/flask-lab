# -*- coding: utf-8 -*-
# @Time : 2025-12-22
# @Author : Yolen
# -----------------------------------------------
from typing import Optional, List

import requests

from harvester.base_harvester import HarvesterBase


class RH3390V2Harvester(HarvesterBase):
    def __init__(self, data):
        super().__init__(data)
        self.monitor_info = {}
        self.uri = f"https://{self.ip}"

    async def create_session(self):
        pass

    def fetch_info(self, target_part: Optional[List[str]] = None):
        for key, value in self.data.items():
            if key == 'login':
                continue
            response = requests.get(url=f"{self.uri}{value}", headers=self.auth_headers)
            if response.status_code == 200:
                self.monitor_info[key] = response.json()

    async def insert_monitor_cpu(self):
        await self._fetch_single(component="cpu", url=self.default_urls.get("cpu").get('url'))
        # 解析结果
        cpu_res = self.collect_data.get("cpu") or []
        monitor_list = []
        for cpu in cpu_res:
            cpu_info = {
                "serial_no": cpu.get("serial_number"),
                "usage": cpu.get("cpu_usage"),
                "core_temp": cpu.get("cpu_temp"),
                "frequency": cpu.get("cpu_frequency"),
                "core_count": cpu.get("cpu_core_count"),
                "model": cpu.get("cpu_model"),
                "dev_id": cpu.get("cpu_id"),
                "health_status": cpu.get("cpu_status"),
            }
            monitor_list.append(cpu_info)
        # 不存在则创建，存在则更新
        self.monitor_info.setdefault("cpu", []).extend(monitor_list)
        return monitor_list
