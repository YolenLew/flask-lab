# -*- coding: utf-8 -*-
# @Time : 2025-12-22
# @Author : Yolen
# -----------------------------------------------
import requests

from harvester.base_harvester import HarvesterBase


class RH3390V2Harvester(HarvesterBase):
    def __init__(self, data):
        super().__init__(data)
        self.monitor_info = {}
        self.uri = f"https://{self.ip}"

    def create_session(self):
        pass

    def fetch_info(self):
        for key, value in self.data.items():
            if key == 'login':
                continue
            response = requests.get(url=f"{self.uri}{value}", headers=self.header)
            if response.status_code == 200:
                self.monitor_info[key] = response.json()
