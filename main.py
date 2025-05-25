# -*- coding: utf-8 -*-
# @Time : 2025/5/25
# @Author : Yolen
# -----------------------------------------------
from app.lab import create_app

APP = create_app()

# 官方原文：
# 请务必把 app.run() 放在 if __name__ == '__main__': 内部或者放在单独 的文件中，这样可以保证它不会被调用。
if __name__ == '__main__':
    APP.run()
