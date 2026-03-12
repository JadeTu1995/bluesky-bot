"""
定时任务调度模块
使用APScheduler实现定时任务
"""

import logging
import random
from datetime import datetime, time, timedelta
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

logger = logging.getLogger(__name__)


class BlueskyScheduler:
    """Bluesky自动推文定时调度器"""

    def __init__(self):
        """初始化调度器"""
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("定时调度器已启动")

    def schedule_morning_post(
        self,
        job_func: Callable,
        *args,
        **kwargs
    ) -> Optional[str]:
        """
        调度早上9-10点随机时间发送推文

        Args:
            job_func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            Optional[str]: 任务ID
        """
        # 生成9:00-10:00之间的随机时间
        random_hour = 9
        random_minute = random.randint(0, 59)
        random_second = random.randint(0, 59)

        trigger = CronTrigger(
            hour=random_hour,
            minute=random_minute,
            second=random_second
        )

        job_id = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            id='morning_post',
            name='早上Bluesky推文',
            replace_existing=True
        )

        logger.info(f"已调度早上推文任务: {random_hour:02d}:{random_minute:02d}:{random_second:02d}")
        return job_id

    def schedule_afternoon_post(
        self,
        job_func: Callable,
        *args,
        **kwargs
    ) -> Optional[str]:
        """
        调度下午16-17点随机时间发送推文

        Args:
            job_func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            Optional[str]: 任务ID
        """
        # 生成16:00-17:00之间的随机时间
        random_hour = 16
        random_minute = random.randint(0, 59)
        random_second = random.randint(0, 59)

        trigger = CronTrigger(
            hour=random_hour,
            minute=random_minute,
            second=random_second
        )

        job_id = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            id='afternoon_post',
            name='下午Bluesky推文',
            replace_existing=True
        )

        logger.info(f"已调度下午推文任务: {random_hour:02d}:{random_minute:02d}:{random_second:02d}")
        return job_id

    def schedule_custom_post(
        self,
        job_func: Callable,
        run_time: datetime,
        *args,
        **kwargs
    ) -> Optional[str]:
        """
        调度指定时间的推文

        Args:
            job_func: 要执行的函数
            run_time: 执行时间
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            Optional[str]: 任务ID
        """
        trigger = DateTrigger(run_date=run_time)

        job_id = self.scheduler.add_job(
            job_func,
            trigger=trigger,
            args=args,
            kwargs=kwargs,
            name=f'定时推文 {run_time}'
        )

        logger.info(f"已调度定时推文任务: {run_time}")
        return job_id

    def reschedule_random_times(self):
        """重新随机化早上和下午的推文时间"""
        # 移除现有任务
        if self.scheduler.get_job('morning_post'):
            self.scheduler.remove_job('morning_post')
            logger.info("已移除早上推文任务")

        if self.scheduler.get_job('afternoon_post'):
            self.scheduler.remove_job('afternoon_post')
            logger.info("已移除下午推文任务")

    def get_job_info(self, job_id: str) -> Optional[dict]:
        """
        获取任务信息

        Args:
            job_id: 任务ID

        Returns:
            Optional[dict]: 任务信息
        """
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            }
        return None

    def list_jobs(self) -> list:
        """
        列出所有任务

        Returns:
            list: 任务列表
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs

    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        logger.info("定时调度器已关闭")


def get_random_morning_time() -> time:
    """
    获取早上9-10点之间的随机时间

    Returns:
        time: 随机时间
    """
    random_minute = random.randint(0, 59)
    random_second = random.randint(0, 59)
    return time(hour=9, minute=random_minute, second=random_second)


def get_random_afternoon_time() -> time:
    """
    获取下午16-17点之间的随机时间

    Returns:
        time: 随机时间
    """
    random_minute = random.randint(0, 59)
    random_second = random.randint(0, 59)
    return time(hour=16, minute=random_minute, second=random_second)
