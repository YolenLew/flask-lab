# -*- coding: utf-8 -*-
# @Time : 2026-01-31
# @Author : Yolen
# -----------------------------------------------
# -*- coding: utf-8 -*-
# @Time : 2025-12-24
# @Author : Yolen
# -----------------------------------------------
# async_mysql_client.py
import asyncio
import logging
from functools import wraps
from typing import Optional, List, Dict, Any

import aiomysql

logger = logging.getLogger(__name__)


class AsyncMySQLPool:
    """异步MySQL连接池工具类"""

    _lock: asyncio.Lock = asyncio.Lock()
    _pool: Optional[aiomysql.Pool] = None
    _config: Optional[Dict[str, Any]] = None

    @classmethod
    def configure(cls, **kwargs):
        """配置数据库连接参数"""
        cls._config = {
            'host': kwargs.get('host', '192.168.211.110'),
            'port': kwargs.get('port', 3306),
            'user': kwargs.get('user', 'root'),
            'password': kwargs.get('password', 'root'),
            'db': kwargs.get('db', 'test'),
            'charset': kwargs.get('charset', 'utf8mb4'),
            'minsize': kwargs.get('minsize', 1),
            'maxsize': kwargs.get('maxsize', 10),
            'pool_recycle': kwargs.get('pool_recycle', 3600),
            'autocommit': kwargs.get('autocommit', True),
            'echo': kwargs.get('echo', False),
        }
        logger.info(f"MySQL配置已设置: {cls._config['host']}:{cls._config['port']}/{cls._config['db']}")

    @classmethod
    async def _init_pool(cls):
        """初始化连接池（延迟懒加载）"""
        if cls._pool is not None and not cls._pool.closed:
            return

        if cls._config is None:
            raise RuntimeError("请先调用configure()方法配置数据库连接参数")

        async with cls._lock:
            if cls._pool is not None and not cls._pool.closed:
                return

            try:
                cls._pool = await aiomysql.create_pool(**cls._config)
                logger.info("MySQL连接池初始化完成")
            except Exception as e:
                logger.error(f"MySQL连接池初始化失败: {e}")
                raise

    @classmethod
    def ensure_pool(cls, func):
        """装饰器：确保连接池已初始化"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if cls._pool is None or cls._pool.closed:
                await cls._init_pool()
            return await func(*args, **kwargs)

        return wrapper

    @classmethod
    async def get_connection(cls):
        """获取数据库连接上下文管理器"""
        await cls._init_pool()
        return cls._pool.acquire()

    @classmethod
    async def execute(cls, query: str, *args, **kwargs) -> int:
        """执行SQL语句，返回影响的行数"""
        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args or kwargs)
                return cursor.rowcount

    @classmethod
    async def fetch_one(cls, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args or kwargs)
                return await cursor.fetchone()

    @classmethod
    async def fetch_all(cls, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """查询所有记录"""
        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args or kwargs)
                return await cursor.fetchall()

    @classmethod
    async def fetch_many(cls, query: str, size: int = 100, *args, **kwargs) -> List[Dict[str, Any]]:
        """批量查询记录"""
        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args or kwargs)
                return await cursor.fetchmany(size)

    @classmethod
    async def insert(cls, table: str, data: Dict[str, Any]) -> int:
        """插入单条记录，返回插入的ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, list(data.values()))
                return cursor.lastrowid

    @classmethod
    async def insert_many(cls, table: str, data_list: List[Dict[str, Any]]) -> int:
        """批量插入记录，返回影响的行数"""
        if not data_list:
            return 0

        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(data_list[0]))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        values = [tuple(item.values()) for item in data_list]

        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.executemany(query, values)
                return cursor.rowcount

    @classmethod
    async def update(cls, table: str, data: Dict[str, Any], where: str, *args, **kwargs) -> int:
        """更新记录"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"

        params = list(data.values()) + list(args or list(kwargs.values()))

        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return cursor.rowcount

    @classmethod
    async def delete(cls, table: str, where: str, *args, **kwargs) -> int:
        """删除记录"""
        query = f"DELETE FROM {table} WHERE {where}"

        async with (await cls.get_connection()) as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args or kwargs)
                return cursor.rowcount

    @classmethod
    async def transaction(cls):
        """事务上下文管理器"""
        await cls._ensure_pool()
        conn = await cls._pool.acquire()

        class TransactionContext:
            def __init__(self, conn):
                self.conn = conn
                self.closed = False

            async def __aenter__(self):
                await self.conn.begin()
                return self.conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                try:
                    if exc_type is not None:
                        await self.conn.rollback()
                        logger.error(f"事务回滚: {exc_val}")
                    else:
                        await self.conn.commit()
                finally:
                    if not self.closed:
                        cls._pool.release(self.conn)
                        self.closed = True

        return TransactionContext(conn)

    @classmethod
    async def health_check(cls) -> bool:
        """健康检查"""
        try:
            async with (await cls.get_connection()) as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False

    @classmethod
    async def close(cls):
        """关闭连接池"""
        if cls._pool is None or cls._pool.closed:
            return

        async with cls._lock:
            if cls._pool is None or cls._pool.closed:
                return

            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("MySQL连接池已关闭")


# 使用示例
async def example_usage():
    # 配置数据库连接
    AsyncMySQLPool.configure(
        host='192.168.211.110',
        port=3306,
        user='root',
        password='root',
        db='test',
        minsize=1,
        maxsize=10
    )

    try:
        # 查询示例
        user = await AsyncMySQLPool.fetch_one(
            "SELECT * FROM t_user WHERE id = %s",
            1
        )
        print(f"id:1, user:{user}")

        # 插入示例
        user_id = await AsyncMySQLPool.insert('t_user', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 30
        })

        # 更新示例
        affected = await AsyncMySQLPool.update(
            't_user',
            {'age': 31},
            'id = %s',
            user_id
        )
        print(f"affected: {affected}")

        # 批量插入示例
        users = [
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 28},
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 32}
        ]
        insert_row = await AsyncMySQLPool.insert_many('t_user', users)
        print(f"insert_row: {insert_row}")

    finally:
        # 关闭连接池
        await AsyncMySQLPool.close()


if __name__ == '__main__':
    asyncio.run(example_usage())
