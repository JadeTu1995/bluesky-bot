"""
Bluesky自动推文机器人主程序
从飞书多维表格读取文章并自动发布到Bluesky
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from coze_workload_identity import Client
from cozeloop.decorator import observe
from tools.bluesky_tool import BlueskyClient, create_bluesky_post_text
from utils.scheduler import BlueskyScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BlueskyBot:
    """Bluesky自动推文机器人"""

    def __init__(
        self,
        bluesky_handle: str,
        bluesky_password: str,
        feishu_app_token: str,
        feishu_table_id: str
    ):
        """
        初始化机器人

        Args:
            bluesky_handle: Bluesky账号
            bluesky_password: Bluesky密码
            feishu_app_token: 飞书多维表格app_token
            feishu_table_id: 飞书表格table_id
        """
        self.bluesky_handle = bluesky_handle
        self.bluesky_password = bluesky_password
        self.feishu_app_token = feishu_app_token
        self.feishu_table_id = feishu_table_id

        self.bluesky_client = BlueskyClient(
            handle=bluesky_handle,
            password=bluesky_password
        )
        self.scheduler = BlueskyScheduler()

    def get_feishu_access_token(self) -> str:
        """获取飞书访问令牌"""
        client = Client()
        return client.get_integration_credential("integration-feishu-base")

    @observe
    def get_feishu_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        从飞书获取单条记录

        Args:
            record_id: 记录ID

        Returns:
            Optional[Dict[str, Any]]: 记录数据
        """
        try:
            access_token = self.get_feishu_access_token()
            url = f"https://open.larkoffice.com/open-apis/bitable/v1/apps/{self.feishu_app_token}/tables/{self.feishu_table_id}/records/{record_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            response = requests.get(url, headers=headers)
            data = response.json()

            if data.get("code") == 0:
                return data.get("data")
            else:
                logger.error(f"获取飞书记录失败: {data}")
                return None
        except Exception as e:
            logger.error(f"获取飞书记录异常: {str(e)}")
            return None

    @observe
    def update_feishu_record(
        self,
        record_id: str,
        fields: Dict[str, Any]
    ) -> bool:
        """
        更新飞书记录

        Args:
            record_id: 记录ID
            fields: 要更新的字段

        Returns:
            bool: 更新是否成功
        """
        try:
            access_token = self.get_feishu_access_token()
            url = f"https://open.larkoffice.com/open-apis/bitable/v1/apps/{self.feishu_app_token}/tables/{self.feishu_table_id}/records/{record_id}"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            body = {
                "fields": fields
            }

            response = requests.patch(url, headers=headers, json=body)
            data = response.json()

            if data.get("code") == 0:
                logger.info(f"飞书记录更新成功: {record_id}")
                return True
            else:
                logger.error(f"飞书记录更新失败: {data}")
                return False
        except Exception as e:
            logger.error(f"飞书记录更新异常: {str(e)}")
            return False

    @observe
    def search_pending_articles(self) -> Optional[list]:
        """
        搜索未发送的文章

        Returns:
            Optional[list]: 未发送的文章列表
        """
        try:
            access_token = self.get_feishu_access_token()
            url = f"https://open.larkoffice.com/open-apis/bitable/v1/apps/{self.feishu_app_token}/tables/{self.feishu_table_id}/records/search"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            # 筛选条件：发送状态为"未发送"
            body = {
                "filter": {
                    "conjunction": "and",
                    "conditions": [
                        {
                            "field_name": "发送状态",
                            "operator": "is",
                            "value": ["未发送"]
                        }
                    ]
                },
                "sort": [
                    {
                        "field_name": "创建时间",
                        "desc": False
                    }
                ],
                "page_size": 10
            }

            response = requests.post(url, headers=headers, json=body)
            data = response.json()

            if data.get("code") == 0:
                records = data.get("data", {}).get("items", [])
                logger.info(f"找到 {len(records)} 条未发送文章")
                return records
            else:
                logger.error(f"搜索飞书记录失败: {data}")
                return None
        except Exception as e:
            logger.error(f"搜索飞书记录异常: {str(e)}")
            return None

    def download_image(self, image_url: str) -> Optional[bytes]:
        """
        下载图片

        Args:
            image_url: 图片URL

        Returns:
            Optional[bytes]: 图片二进制数据
        """
        try:
            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"下载图片失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"下载图片异常: {str(e)}")
            return None

    def post_article(self, article_record: Dict[str, Any]) -> bool:
        """
        发布文章到Bluesky

        Args:
            article_record: 文章记录

        Returns:
            bool: 发布是否成功
        """
        try:
            fields = article_record.get("fields", {})
            record_id = article_record.get("record_id")

            # 获取文章信息
            title = fields.get("标题", "")
            doi_link = fields.get("DOI链接", "")
            toc_image_url = fields.get("TOC图片", "")
            
            if not title:
                logger.error("文章标题为空")
                return False

            # 下载TOC图片
            image_bytes = None
            if toc_image_url:
                image_bytes = self.download_image(toc_image_url)

            # 登录Bluesky
            if not self.bluesky_client.login():
                logger.error("Bluesky登录失败")
                return False

            # 创建推文文本
            post_text = create_bluesky_post_text(title, doi_link)

            # 发布推文
            post_uri = None
            if image_bytes:
                post_uri = self.bluesky_client.send_post_with_image(
                    text=post_text,
                    image_bytes=image_bytes,
                    image_alt=f"TOC image for {title}"
                )
            else:
                post_uri = self.bluesky_client.send_post(text=post_text)

            if not post_uri:
                logger.error("推文发布失败")
                return False

            # 更新飞书记录
            update_fields = {
                "发送状态": "已发送",
                "发送时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Bluesky推文URI": post_uri
            }

            if self.update_feishu_record(record_id, update_fields):
                logger.info(f"文章发布成功: {title}")
                return True
            else:
                logger.warning("推文发布成功，但飞书记录更新失败")
                return False

        except Exception as e:
            logger.error(f"发布文章异常: {str(e)}")
            return False

    def post_next_article(self) -> bool:
        """
        发布下一条未发送的文章

        Returns:
            bool: 发布是否成功
        """
        logger.info("开始检查未发送的文章...")

        # 获取未发送的文章
        pending_articles = self.search_pending_articles()

        if not pending_articles:
            logger.info("没有未发送的文章")
            return True

        # 发布第一条文章
        article_record = pending_articles[0]
        return self.post_article(article_record)

    def start_scheduler(self):
        """启动定时任务"""
        # 调度早上9-10点随机时间
        self.scheduler.schedule_morning_post(self.post_next_article)

        # 调度下午16-17点随机时间
        self.scheduler.schedule_afternoon_post(self.post_next_article)

        logger.info("定时任务已启动")

    def run_once(self):
        """立即执行一次发布（用于测试）"""
        logger.info("立即执行发布任务...")
        self.post_next_article()

    def run_forever(self):
        """持续运行（阻塞）"""
        logger.info("机器人已启动，等待定时任务...")
        try:
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
            self.scheduler.shutdown()


def main():
    """主函数"""
    # 从环境变量读取配置
    bluesky_handle = os.getenv("BLUESKY_HANDLE")
    bluesky_password = os.getenv("BLUESKY_PASSWORD")
    feishu_app_token = os.getenv("FEISHU_APP_TOKEN")
    feishu_table_id = os.getenv("FEISHU_TABLE_ID")

    # 检查必需的环境变量
    if not all([bluesky_handle, bluesky_password, feishu_app_token, feishu_table_id]):
        logger.error("缺少必需的环境变量")
        logger.error("请设置: BLUESKY_HANDLE, BLUESKY_PASSWORD, FEISHU_APP_TOKEN, FEISHU_TABLE_ID")
        return

    # 创建机器人实例
    bot = BlueskyBot(
        bluesky_handle=bluesky_handle,
        bluesky_password=bluesky_password,
        feishu_app_token=feishu_app_token,
        feishu_table_id=feishu_table_id
    )

    # 启动定时任务
    bot.start_scheduler()

    # 持续运行
    bot.run_forever()


if __name__ == "__main__":
    main()
