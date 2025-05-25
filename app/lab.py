# -*- coding: utf-8 -*-
# @Time : 2025/5/25
# @Author : Yolen
# -----------------------------------------------
from flask import Flask


def create_app():
    app = Flask(__name__)
    return app