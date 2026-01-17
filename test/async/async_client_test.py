# -*- coding: utf-8 -*-
# @Time : 2025-12-27
# @Author : Yolen
# -----------------------------------------------
import asyncio

import aiohttp

from config.async_client_config import AsyncHTTPClientPool
from infra.util.m_async_timer import m_async_timed


@m_async_timed()
async def fetch_status(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as response:
        return response.status

@m_async_timed()
async def main():
    client = AsyncHTTPClientPool()
    session = await client.get_session()
    urls = ["https://www.example.com" for _ in range(1000)]
    tasks = [asyncio.create_task(fetch_status(session, url)) for url in urls]
    await asyncio.wait(tasks)
    # print(f"tasks done: {[task.result() for task in tasks]}")
    await client.close()

# finish <function main at 0x0000029B63E9A0D0> in 15.5115 seconds
asyncio.run(main())

