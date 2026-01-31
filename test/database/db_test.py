# -*- coding: utf-8 -*-
# @Time : 2026-01-31
# @Author : Yolen
# -----------------------------------------------
import asyncio
import concurrent
import logging
import random
import string
import time
from typing import Dict, List, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 导入刚才的两个MySQL连接池类
# 注意：这里假设上面的代码已经保存为 async_mysql_client.py
# 实际使用时可能需要调整导入方式


def generate_random_user_data(num: int) -> List[Dict[str, any]]:
    """生成随机用户数据"""
    users = []
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'example.com', 'test.com']

    for i in range(num):
        # 生成随机姓名
        name_length = random.randint(5, 15)
        name = ''.join(random.choices(string.ascii_letters, k=name_length))

        # 生成随机邮箱
        email_prefix = ''.join(random.choices(string.ascii_lowercase, k=8))
        email_domain = random.choice(domains)
        email = f"{email_prefix}@{email_domain}"

        # 生成随机年龄
        age = random.randint(18, 80)

        users.append({
            'name': name,
            'email': email,
            'age': age
        })

    return users


class PerformanceTest:
    """性能测试类"""

    def __init__(self, host='192.168.211.110', port=3306, user='root',
                 password='root', db='test'):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db

        # 生成测试数据（10万条）
        logger.info("开始生成测试数据...")
        self.test_data = generate_random_user_data(1000000)
        logger.info(f"测试数据生成完成，共 {len(self.test_data)} 条")

    def prepare_test_table(self):
        """准备测试表（如果不存在则创建）"""
        # 使用同步连接池创建表
        from infra.client.sync_database import SyncMySQLPool

        SyncMySQLPool.configure(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db
        )

        create_table_sql = """
                           CREATE TABLE `t_user`
                           (
                               `id`           bigint(20) NOT NULL AUTO_INCREMENT COMMENT 'ID',
                               `name`         varchar(255)      DEFAULT NULL COMMENT '姓名',
                               `age`          int(11) DEFAULT NULL COMMENT '年龄',
                               `email`        varchar(255)      DEFAULT NULL COMMENT '邮箱',
                               `created_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                               `updated_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                               PRIMARY KEY (`id`) USING BTREE
                           ) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8 ROW_FORMAT=DYNAMIC COMMENT='用户表';
                           """

        try:
            # 创建表
            SyncMySQLPool.execute(create_table_sql)
            logger.info("测试表创建/检查完成")
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            raise

        # 清理现有数据（可选）
        try:
            SyncMySQLPool.execute("TRUNCATE TABLE t_user")
            logger.info("已清空测试表")
        except Exception as e:
            logger.warning(f"清空表失败，可能表不存在: {e}")

        SyncMySQLPool.close()

    async def test_async_batch_insert(self, batch_size: int = 1000) -> Dict[str, any]:
        """测试异步批量插入性能"""
        from infra.client.async_database import AsyncMySQLPool

        # 配置异步连接池
        AsyncMySQLPool.configure(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.db,
            minsize=10,  # 增加最小连接数
            maxsize=50  # 增加最大连接数
        )

        logger.info(f"开始异步批量插入测试，批量大小: {batch_size}")
        start_time = time.time()

        # 分批插入
        total_rows = len(self.test_data)
        inserted_count = 0

        for i in range(0, total_rows, batch_size):
            batch_data = self.test_data[i:i + batch_size]

            try:
                rows = await AsyncMySQLPool.insert_many('t_user', batch_data)
                inserted_count += rows

                # 每插入1万条记录一次进度
                if (i + batch_size) % 10000 == 0:
                    progress = min(i + batch_size, total_rows)
                    logger.info(f"异步插入进度: {progress}/{total_rows} ({progress / total_rows * 100:.1f}%)")

            except Exception as e:
                logger.error(f"异步批量插入失败（批次 {i // batch_size + 1}）: {e}")
                # 继续尝试下一批
                continue

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 验证插入的数据量
        try:
            result = await AsyncMySQLPool.fetch_one("SELECT COUNT(*) as count FROM t_user")
            actual_count = result['count'] if result else 0
        except:
            actual_count = 0

        # 关闭连接池
        await AsyncMySQLPool.close()

        logger.info(
            f"完成异步批量插入测试，批量大小: {batch_size}，总数据量: {total_rows}，耗时: {elapsed_time:.2f}秒，插入数据量: {inserted_count}，实际数据量: {actual_count}，每秒处理数据量: {inserted_count / elapsed_time:.2f}")
        return {
            'method': '异步批量插入',
            'batch_size': batch_size,
            'total_data': total_rows,
            'inserted_count': inserted_count,
            'actual_count': actual_count,
            'elapsed_time': elapsed_time,
            'rows_per_second': inserted_count / elapsed_time if elapsed_time > 0 else 0
        }

    async def test_async_single_insert(self) -> Dict[str, any]:
        """测试异步单条插入性能"""
        from infra.client.async_database import AsyncMySQLPool

        # 配置异步连接池
        AsyncMySQLPool.configure(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.db,
            minsize=10,
            maxsize=50
        )

        logger.info("开始异步单条插入测试")
        start_time = time.time()

        total_rows = len(self.test_data)
        inserted_count = 0

        for i, user_data in enumerate(self.test_data):
            try:
                await AsyncMySQLPool.insert('t_user', user_data)
                inserted_count += 1

                # 每插入1000条记录一次进度
                if (i + 1) % 1000 == 0:
                    logger.info(f"异步单条插入进度: {i + 1}/{total_rows} ({(i + 1) / total_rows * 100:.1f}%)")

            except Exception as e:
                logger.error(f"异步单条插入失败（第 {i + 1} 条）: {e}")
                # 继续尝试下一条
                continue

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 验证插入的数据量
        try:
            result = await AsyncMySQLPool.fetch_one("SELECT COUNT(*) as count FROM t_user")
            actual_count = result['count'] if result else 0
        except:
            actual_count = 0

        # 关闭连接池
        await AsyncMySQLPool.close()

        return {
            'method': '异步单条插入',
            'total_data': total_rows,
            'inserted_count': inserted_count,
            'actual_count': actual_count,
            'elapsed_time': elapsed_time,
            'rows_per_second': inserted_count / elapsed_time if elapsed_time > 0 else 0
        }

    def test_sync_batch_insert(self, batch_size: int = 1000) -> Dict[str, any]:
        """测试同步批量插入性能"""
        from infra.client.sync_database import SyncMySQLPool

        # 配置同步连接池
        SyncMySQLPool.configure(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db,
            mincached=10,  # 增加最小缓存连接数
            maxcached=50  # 增加最大缓存连接数
        )

        logger.info(f"开始同步批量插入测试，批量大小: {batch_size}")
        start_time = time.time()

        # 分批插入
        total_rows = len(self.test_data)
        inserted_count = 0

        for i in range(0, total_rows, batch_size):
            batch_data = self.test_data[i:i + batch_size]

            try:
                rows = SyncMySQLPool.insert_many('t_user', batch_data)
                inserted_count += rows

                # 每插入1万条记录一次进度
                if (i + batch_size) % 10000 == 0:
                    progress = min(i + batch_size, total_rows)
                    logger.info(f"同步插入进度: {progress}/{total_rows} ({progress / total_rows * 100:.1f}%)")

            except Exception as e:
                logger.error(f"同步批量插入失败（批次 {i // batch_size + 1}）: {e}")
                # 继续尝试下一批
                continue

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 验证插入的数据量
        try:
            result = SyncMySQLPool.fetch_one("SELECT COUNT(*) as count FROM t_user")
            actual_count = result['count'] if result else 0
        except:
            actual_count = 0

        # 关闭连接池
        SyncMySQLPool.close()

        logger.info(
            f"完成同步批量插入测试，批量大小: {batch_size}，总数据量: {total_rows}，耗时: {elapsed_time:.2f}秒，插入数据量: {inserted_count}，实际数据量: {actual_count}，每秒处理数据量: {inserted_count / elapsed_time:.2f}")
        return {
            'method': '同步批量插入',
            'batch_size': batch_size,
            'total_data': total_rows,
            'inserted_count': inserted_count,
            'actual_count': actual_count,
            'elapsed_time': elapsed_time,
            'rows_per_second': inserted_count / elapsed_time if elapsed_time > 0 else 0
        }

    def test_threadpool_executor_batch_insert(self, batch_size: int = 1000,
                                              max_workers: int = 100) -> Dict[str, any]:
        """使用ThreadPoolExecutor进行并发批量插入测试"""
        from infra.client.sync_database import SyncMySQLPool

        # 配置同步连接池
        SyncMySQLPool.configure(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db,
            mincached=10,
            maxcached=50,
            maxconnections=50
        )

        logger.info(f"开始ThreadPoolExecutor并发批量插入测试，最大工作线程: {max_workers}，批量大小: {batch_size}")
        start_time = time.time()

        # 准备数据批次
        total_rows = len(self.test_data)
        batches = []

        for i in range(0, total_rows, batch_size):
            batches.append(self.test_data[i:i + batch_size])

        total_batches = len(batches)
        logger.info(f"总批次数: {total_batches}，每批约 {batch_size} 条记录")

        inserted_total = 0
        error_count = 0

        # 定义工作函数
        def insert_batch(batch_data: List[Dict[str, any]], batch_num: int) -> Tuple[int, int]:
            """插入单个批次，返回成功插入的行数和错误数"""
            try:
                rows = SyncMySQLPool.insert_many('t_user', batch_data)

                # 每完成10%的批次记录一次进度
                if batch_num % max(1, total_batches // 10) == 0:
                    logger.info(f"批次 {batch_num}/{total_batches} 已完成")

                return rows, 0
            except Exception as e:
                logger.error(f"批次 {batch_num} 插入失败: {e}")
                return 0, 1

        # 使用ThreadPoolExecutor并发执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_batch = {
                executor.submit(insert_batch, batch_data, i + 1): i + 1
                for i, batch_data in enumerate(batches)
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    rows, errors = future.result()
                    inserted_total += rows
                    error_count += errors
                except Exception as e:
                    logger.error(f"批次 {batch_num} 执行异常: {e}")
                    error_count += 1

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 验证插入的数据量
        try:
            result = SyncMySQLPool.fetch_one("SELECT COUNT(*) as count FROM t_user")
            actual_count = result['count'] if result else 0
        except:
            actual_count = 0

        # 关闭连接池
        SyncMySQLPool.close()

        logger.info(
            f"完成ThreadPoolExecutor并发批量插入测试，最大工作线程: {max_workers}，批量大小: {batch_size}，总批次数: {total_batches}，总数据量: {total_rows}，耗时: {elapsed_time:.2f}秒，插入数据量: {inserted_total}，实际数据量: {actual_count}，错误数: {error_count}，每秒处理数据量: {inserted_total / elapsed_time:.2f}")
        return {
            'method': 'ThreadPoolExecutor并发批量插入',
            'max_workers': max_workers,
            'batch_size': batch_size,
            'total_batches': total_batches,
            'total_data': total_rows,
            'inserted_count': inserted_total,
            'actual_count': actual_count,
            'error_count': error_count,
            'elapsed_time': elapsed_time,
            'rows_per_second': inserted_total / elapsed_time if elapsed_time > 0 else 0
        }

    def test_sync_single_insert(self) -> Dict[str, any]:
        """测试同步单条插入性能"""
        from infra.client.sync_database import SyncMySQLPool

        # 配置同步连接池
        SyncMySQLPool.configure(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.db,
            mincached=10,
            maxcached=50
        )

        logger.info("开始同步单条插入测试")
        start_time = time.time()

        total_rows = len(self.test_data)
        inserted_count = 0

        for i, user_data in enumerate(self.test_data):
            try:
                SyncMySQLPool.insert('t_user', user_data)
                inserted_count += 1

                # 每插入1000条记录一次进度
                if (i + 1) % 1000 == 0:
                    logger.info(f"同步单条插入进度: {i + 1}/{total_rows} ({(i + 1) / total_rows * 100:.1f}%)")

            except Exception as e:
                logger.error(f"同步单条插入失败（第 {i + 1} 条）: {e}")
                # 继续尝试下一条
                continue

        end_time = time.time()
        elapsed_time = end_time - start_time

        # 验证插入的数据量
        try:
            result = SyncMySQLPool.fetch_one("SELECT COUNT(*) as count FROM t_user")
            actual_count = result['count'] if result else 0
        except:
            actual_count = 0

        # 关闭连接池
        SyncMySQLPool.close()

        return {
            'method': '同步单条插入',
            'total_data': total_rows,
            'inserted_count': inserted_count,
            'actual_count': actual_count,
            'elapsed_time': elapsed_time,
            'rows_per_second': inserted_count / elapsed_time if elapsed_time > 0 else 0
        }

    def print_results(self, results: List[Dict[str, any]]):
        """打印测试结果"""
        print("\n" + "=" * 80)
        print("MySQL连接池性能测试结果")
        print("=" * 80)

        for result in results:
            print(f"\n{result['method']}:")
            print(f"  插入数据量: {result['inserted_count']:,} / {result['total_data']:,}")
            print(f"  数据库实际记录数: {result['actual_count']:,}")
            print(f"  耗时: {result['elapsed_time']:.2f} 秒")
            print(f"  插入速度: {result['rows_per_second']:,.2f} 条/秒")
            if 'batch_size' in result:
                print(f"  批量大小: {result['batch_size']}")

        print("\n" + "=" * 80)
        print("性能对比分析:")
        print("=" * 80)

        # 找出最快的方法
        fastest = max(results, key=lambda x: x['rows_per_second'])
        slowest = min(results, key=lambda x: x['rows_per_second'])

        print(f"\n最快的方法: {fastest['method']} ({fastest['rows_per_second']:,.2f} 条/秒)")
        print(f"最慢的方法: {slowest['method']} ({slowest['rows_per_second']:,.2f} 条/秒)")

        # 计算性能提升百分比
        if slowest['rows_per_second'] > 0:
            improvement = (fastest['rows_per_second'] - slowest['rows_per_second']) / slowest['rows_per_second'] * 100
            print(f"性能提升: {improvement:.1f}%")

        # 批量 vs 单条对比
        batch_results = [r for r in results if 'batch_size' in r]
        single_results = [r for r in results if 'batch_size' not in r]

        if batch_results and single_results:
            avg_batch_speed = sum(r['rows_per_second'] for r in batch_results) / len(batch_results)
            avg_single_speed = sum(r['rows_per_second'] for r in single_results) / len(single_results)

            print(f"\n批量插入平均速度: {avg_batch_speed:,.2f} 条/秒")
            print(f"单条插入平均速度: {avg_single_speed:,.2f} 条/秒")

            if avg_single_speed > 0:
                batch_improvement = (avg_batch_speed - avg_single_speed) / avg_single_speed * 100
                print(f"批量插入比单条插入快: {batch_improvement:.1f}%")

        print("\n建议:")
        if fastest['method'].startswith('异步'):
            print("  • 在I/O密集型应用中，异步连接池性能更好")
        else:
            print("  • 在CPU密集型应用中，同步连接池可能表现更好")

        if any('批量' in r['method'] for r in results):
            print("  • 批量插入比单条插入快很多，建议使用批量操作")

        print("=" * 80)


async def main():
    """主函数"""
    print("MySQL连接池性能测试程序")
    print("测试目标: 插入10万条随机数据")
    print("-" * 60)

    # 初始化测试
    test = PerformanceTest(
        host='192.168.211.110',
        port=3306,
        user='root',
        password='root',
        db='test'
    )

    # 准备测试表
    # test.prepare_test_table()

    results = []

    try:
        # 测试1: 同步批量插入
        print("\n>>> 测试1: 同步批量插入")
        result1 = test.test_sync_batch_insert(batch_size=1000)
        results.append(result1)

        # 清空表，准备下一个测试
        from infra.client.sync_database import SyncMySQLPool
        SyncMySQLPool.configure(
            host=test.host,
            port=test.port,
            user=test.user,
            password=test.password,
            database=test.db
        )
        SyncMySQLPool.execute("TRUNCATE TABLE t_user")
        SyncMySQLPool.close()

        # 测试2: 同步单条插入
        print("\n>>> 测试2: 同步单条插入")
        result2 = test.test_sync_single_insert()
        results.append(result2)

        # 清空表
        SyncMySQLPool.configure(
            host=test.host,
            port=test.port,
            user=test.user,
            password=test.password,
            database=test.db
        )
        SyncMySQLPool.execute("TRUNCATE TABLE t_user")
        SyncMySQLPool.close()

        # 测试3: 异步批量插入
        print("\n>>> 测试3: 异步批量插入")
        result3 = await test.test_async_batch_insert(batch_size=1000)
        results.append(result3)

        # 清空表
        SyncMySQLPool.configure(
            host=test.host,
            port=test.port,
            user=test.user,
            password=test.password,
            database=test.db
        )
        SyncMySQLPool.execute("TRUNCATE TABLE t_user")
        SyncMySQLPool.close()

        # 测试4: 异步单条插入
        print("\n>>> 测试4: 异步单条插入")
        result4 = await test.test_async_single_insert()
        results.append(result4)

        # 打印所有结果
        test.print_results(results)

    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def quick_test():
    """快速测试（只测批量插入）"""
    print("MySQL连接池快速性能测试")
    print("测试目标: 插入10万条随机数据（只测试批量插入）")
    print("-" * 60)

    # 初始化测试
    test = PerformanceTest(
        host='192.168.211.110',
        port=3306,
        user='root',
        password='root',
        db='test'
    )

    # 准备测试表
    # test.prepare_test_table()

    results = []

    try:
        # 测试同步批量插入
        print("\n>>> 测试1: 同步批量插入")
        sync_result = test.test_sync_batch_insert(batch_size=1000)
        results.append(sync_result)

        # 清空表
        from infra.client.sync_database import SyncMySQLPool
        SyncMySQLPool.configure(
            host=test.host,
            port=test.port,
            user=test.user,
            password=test.password,
            database=test.db
        )
        SyncMySQLPool.execute("TRUNCATE TABLE t_user")
        SyncMySQLPool.close()

        # 测试异步批量插入
        print("\n>>> 测试2: 异步批量插入")
        async_result = asyncio.run(test.test_async_batch_insert(batch_size=1000))
        results.append(async_result)

        # 测试3: 线程池并发批量插入（使用ThreadPoolExecutor）
        print("\n>>> 测试3: ThreadPoolExecutor并发批量插入")
        threadpool_result = test.test_threadpool_executor_batch_insert(
            batch_size=1000,
            max_workers=100
        )
        results.append(threadpool_result)

        # 清空表
        SyncMySQLPool.configure(
            host=test.host,
            port=test.port,
            user=test.user,
            password=test.password,
            database=test.db
        )
        SyncMySQLPool.execute("TRUNCATE TABLE t_user")
        SyncMySQLPool.close()

        # 打印结果
        test.print_results(results)
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


"""

  插入速度: 35,040.36 条/秒
  批量大小: 1000

同步单条插入:
  插入数据量: 100,000 / 100,000
  数据库实际记录数: 100,000
  耗时: 272.82 秒
  插入速度: 366.54 条/秒

异步批量插入:
  插入数据量: 100,000 / 100,000
  数据库实际记录数: 100,000
  耗时: 2.75 秒
  插入速度: 36,326.96 条/秒
  批量大小: 1000

异步单条插入:
  插入数据量: 100,000 / 100,000
  数据库实际记录数: 100,000
  耗时: 186.65 秒
  插入速度: 535.76 条/秒

================================================================================
性能对比分析:
================================================================================

最快的方法: 异步批量插入 (36,326.96 条/秒)
最慢的方法: 同步单条插入 (366.54 条/秒)
性能提升: 9810.7%

批量插入平均速度: 35,683.66 条/秒
单条插入平均速度: 451.15 条/秒
批量插入比单条插入快: 7809.5%

建议:
  • 在I/O密集型应用中，异步连接池性能更好
  • 批量插入比单条插入快很多，建议使用批量操作
================================================================================

"""
if __name__ == '__main__':
    # import sys
    #
    # if len(sys.argv) > 1 and sys.argv[1] == 'quick':
    #     # 快速测试模式
    #     quick_test()
    # else:
    #     # 完整测试模式
    #     asyncio.run(main())
    quick_test()
