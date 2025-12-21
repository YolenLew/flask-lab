# -*- coding: utf-8 -*-
# @Time : 2025/5/25
# @Author : Yolen
# -----------------------------------------------
import asyncio

from flask import Flask, current_app


def create_app():
    app = Flask(__name__)

    @app.before_request
    def before_first_request():
        loop = asyncio.get_event_loop()
        current_app.loop = loop

    return app