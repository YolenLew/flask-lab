# -*- coding: utf-8 -*-
# @Time : 2025-12-13
# @Author : Yolen
# -----------------------------------------------
import functools
import time
from typing import Any, Callable


def m_async_timed(name: str = None):            # 装饰器工厂函数: 支持自定义名称
    def wrapper(func: Callable) -> Callable:    # 实际的装饰器函数
        @functools.wraps(func)                  # 保留原函数的元数据（函数名、文档字符串等）
        async def wrapped(*args: Any, **kwargs: Any) -> Any:    # 定义异步包装函数
            print(f'Starting {name or ""} {func} with args {args}, kwargs {kwargs}')
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                total_time = end - start
                print(f'finish {func} in {total_time:.4f} seconds')
        return wrapped
    return wrapper
