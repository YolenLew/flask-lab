# -*- coding: utf-8 -*-
# @Time : 2026-01-31
# @Author : Yolen
# -----------------------------------------------
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

import pymysql
from dbutils.pooled_db import PooledDB
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)


class SyncMySQLPool:
    """同步MySQL连接池工具类"""

    _pool: Optional[PooledDB] = None
    _config: Optional[Dict[str, Any]] = None

    @classmethod
    def configure(cls, **kwargs):
        """配置数据库连接参数"""
        cls._config = {
            'creator': pymysql,
            'host': kwargs.get('host', '192.168.211.110'),
            'port': kwargs.get('port', 3306),
            'user': kwargs.get('user', 'root'),
            'password': kwargs.get('password', 'root'),
            'database': kwargs.get('database', 'test'),
            'charset': kwargs.get('charset', 'utf8mb4'),
            'mincached': kwargs.get('mincached', 1),
            'maxcached': kwargs.get('maxcached', 10),
            'maxconnections': kwargs.get('maxconnections', 20),
            'blocking': kwargs.get('blocking', True),
            'maxusage': kwargs.get('maxusage', 1000),
            'setsession': kwargs.get('setsession', None),
            'autocommit': kwargs.get('autocommit', True),
            'ping': kwargs.get('ping', 1),  # 1: 从池中获取连接时ping服务器
            'cursorclass': DictCursor,  # 使用DictCursor确保返回字典
        }
        logger.info(f"MySQL配置已设置: {cls._config['host']}:{cls._config['port']}/{cls._config['database']}")

    @classmethod
    def _init_pool(cls):
        """初始化连接池"""
        if cls._pool is not None:
            return

        if cls._config is None:
            cls.configure()

        try:
            cls._pool = PooledDB(**cls._config)
            logger.info("MySQL连接池初始化完成")
        except Exception as e:
            logger.error(f"MySQL连接池初始化失败: {e}")
            raise

    @classmethod
    def get_pool(cls):
        """获取连接池"""
        if cls._pool is None:
            cls._init_pool()
        return cls._pool

    @classmethod
    def get_connection(cls):
        """获取数据库连接（上下文管理器）"""
        pool = cls.get_pool()
        return pool.connection()

    @classmethod
    def execute(cls, query: str, *args, **kwargs) -> int:
        """执行SQL语句，返回影响的行数"""
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, args or kwargs)
                    conn.commit()
                    return cursor.rowcount
                except Exception as e:
                    conn.rollback()
                    logger.error(f"SQL执行失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    def fetch_one(cls, query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """查询单条记录"""
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, args or kwargs)
                    return cursor.fetchone()
                except Exception as e:
                    logger.error(f"查询失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    def fetch_all(cls, query: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """查询所有记录"""
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, args or kwargs)
                    return cursor.fetchall()
                except Exception as e:
                    logger.error(f"查询失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    def fetch_many(cls, query: str, size: int = 100, *args, **kwargs) -> List[Dict[str, Any]]:
        """批量查询记录"""
        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, args or kwargs)
                    return cursor.fetchmany(size)
                except Exception as e:
                    logger.error(f"查询失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    def insert(cls, table: str, data: Dict[str, Any]) -> int:
        """插入单条记录，返回插入的ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, list(data.values()))
                    conn.commit()
                    return cursor.lastrowid
                except Exception as e:
                    conn.rollback()
                    logger.error(f"插入失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    def insert_many(cls, table: str, data_list: List[Dict[str, Any]]) -> int:
        """批量插入记录，返回影响的行数"""
        if not data_list:
            return 0

        columns = ', '.join(data_list[0].keys())
        placeholders = ', '.join(['%s'] * len(data_list[0]))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        values = [tuple(item.values()) for item in data_list]

        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.executemany(query, values)
                    conn.commit()
                    return cursor.rowcount
                except Exception as e:
                    conn.rollback()
                    logger.error(f"批量插入失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    def update(cls, table: str, data: Dict[str, Any], where: str, *args, **kwargs) -> int:
        """更新记录"""
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"

        params = list(data.values()) + list(args or list(kwargs.values()))

        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, params)
                    conn.commit()
                    return cursor.rowcount
                except Exception as e:
                    conn.rollback()
                    logger.error(f"更新失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    def delete(cls, table: str, where: str, *args, **kwargs) -> int:
        """删除记录"""
        query = f"DELETE FROM {table} WHERE {where}"

        with cls.get_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, args or kwargs)
                    conn.commit()
                    return cursor.rowcount
                except Exception as e:
                    conn.rollback()
                    logger.error(f"删除失败: {query[:100]}, error: {e}")
                    raise

    @classmethod
    @contextmanager
    def transaction(cls):
        """事务上下文管理器"""
        conn = cls.get_pool().connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"事务执行失败: {e}")
            raise
        finally:
            conn.close()

    @classmethod
    def health_check(cls) -> bool:
        """健康检查"""
        try:
            with cls.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    # 检查结果是否存在，并且第一个字段的值为1: {'1':1}
                    return result is not None and list(result.values())[0] == 1
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False

    @classmethod
    def close(cls):
        """关闭连接池"""
        if cls._pool is not None:
            cls._pool.close()
            cls._pool = None
            logger.info("MySQL连接池已关闭")


# 使用示例
def example_usage():
    # 配置数据库连接
    SyncMySQLPool.configure()

    try:
        # 健康检查
        is_healthy = SyncMySQLPool.health_check()
        print(f"数据库健康状态: {is_healthy}")

        # 查询示例
        user = SyncMySQLPool.fetch_one(
            "SELECT * FROM t_user WHERE id = %s",
            1
        )
        print(f"查询用户: {user}")

        # 插入示例
        user_id = SyncMySQLPool.insert('t_user', {
            'name': 'John Doe',
            'email': 'john@example.com',
            'age': 30
        })
        print(f"插入用户ID: {user_id}")

        # 更新示例
        affected = SyncMySQLPool.update(
            't_user',
            {'age': 31},
            'id = %s',
            user_id
        )
        print(f"更新影响行数: {affected}")

        # 批量插入示例
        users = [
            {'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
            {'name': 'Bob', 'email': 'bob@example.com', 'age': 28},
            {'name': 'Charlie', 'email': 'charlie@example.com', 'age': 32}
        ]
        SyncMySQLPool.insert_many('t_user', users)

        # 直接使用连接示例
        with SyncMySQLPool.get_connection() as conn:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM t_user")
                result = cursor.fetchone()
                print(f"用户总数: {result['count']}")

    except Exception as e:
        print(f"操作失败: {e}")
    finally:
        # 关闭连接池
        SyncMySQLPool.close()


if __name__ == '__main__':
    example_usage()
