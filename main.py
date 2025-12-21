# -*- coding: utf-8 -*-
# @Time : 2025/5/25
# @Author : Yolen
# -----------------------------------------------
import asyncio

from hypercorn import Config
from hypercorn.asyncio import serve

from app.lab import create_app

app = create_app()

@app.route("/async")
async def async_route():
    await asyncio.sleep(2)
    return {"Hello": "World"}

@app.route("/sync")
def sync_route():
    return {"Hello": "World"}

# 官方原文：
# 请务必把 app.run() 放在 if __name__ == '__main__': 内部或者放在单独 的文件中，这样可以保证它不会被调用。
if __name__ == '__main__':
    config = Config()
    config.bind = ["127.0.0.1:8086"]
    config.workers = 1  # 关键：强制单Worker
    asyncio.run(serve(app, config))
    # app.run(host='127.0.0.1', port=8086)
