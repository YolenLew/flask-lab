# -*- coding: utf-8 -*-
# @Time : 2025-12-17
# @Author : Yolen
# -----------------------------------------------
import functools
import time
from typing import Callable, Any


def sync_timed(name: str = None):
    def wrapper(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            print(f'Sync starting {name or ""} {func} with args {args}, kwargs {kwargs}')
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                end = time.perf_counter()
                total = end - start
                print(f"Sync finished in {total:.4f} seconds")

        return wrapped

    return wrapper
