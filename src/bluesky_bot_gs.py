"""
Bluesky自动推文机器人主程序（Google Sheets版本）
从Google Sheets读取文章并自动发布到Bluesky
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from tools.bluesky_tool import BlueskyClient
from tools.google_sheets_tool import GoogleSheetsClient
from utils.scheduler import BlueskyScheduler
from utils.post_utils import create_post_with_facets

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BlueskyBot:
    """Bluesky自动推文机器人（Google Sheets版本）"""

    def __init__(
        self,
        bluesky_handle: str,
        bluesky_password: str,
        google_credentials_file: str,
        google_spreadsheet_id: str
    ):
        """
        初始化机器人

        Args:
            bluesky_handle: Bluesky账号
            bluesky_password: Bluesky密码
            google_credentials_file: Google Cloud服务账号JSON文件路径
            google_spreadsheet_id: Google表格ID
        """
        self.bluesky_handle = bluesky_handle
        self.bluesky_password = bluesky_password
        self.google_credentials_file = google_credentials_file
        self.google_spreadsheet_id = google_spreadsheet_id

        self.bluesky_client = BlueskyClient(
            handle=bluesky_handle,
            password=bluesky_password
        )
        self.google_client = GoogleSheetsClient(
            credentials_file=google_credentials_file,
            spreadsheet_id=google_spreadsheet_id
        )
        self.scheduler = BlueskyScheduler()

    def download_image(self, image_url: str) -> Optional[bytes]:
        """
        下载图片

        Args:
            image_url: 图片URL

        Returns:
            Optional[bytes]: 图片二进制数据
        """
        try:
            from utils.image_downloader import download_image

            image_bytes, content_type, error = download_image(image_url)

            if error:
                logger.error(f"下载图片失败: {error}")
                return None

            return image_bytes
        except Exception as e:
            logger.error(f"下载图片异常: {str(e)}")
            return None

    def post_article(self, article_data: Dict[str, Any], row_number: int) -> bool:
        """
        发布文章到Bluesky

        Args:
            article_data: 文章数据
            row_number: 在Google Sheets中的行号

        Returns:
            bool: 发布是否成功
        """
        try:
            # 获取文章信息
            title = article_data.get("标题", "")
            doi_link = article_data.get("DOI链接", "")
            toc_image_url = article_data.get("TOC图片", "").strip()

            if not title:
                logger.error("文章标题为空")
                return False

            # 登录Bluesky
            if not self.bluesky_client.login():
                logger.error("Bluesky登录失败")
                return False

            # 创建推文文本和facets
            post_text, post_facets = create_post_with_facets(title, doi_link)

            # 获取TOC图片
            image_bytes = None
            if toc_image_url and toc_image_url.lower() != 'n/a':
                logger.info(f"获取TOC图片: {toc_image_url}")

                # 检查是否是文件名（不是URL）
                if not toc_image_url.startswith('http'):
                    # 从assets目录读取
                    image_path = os.path.join(os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects"), 'assets', toc_image_url)
                    logger.info(f"从assets目录读取图片: {image_path}")

                    if os.path.exists(image_path):
                        try:
                            with open(image_path, 'rb') as f:
                                image_bytes = f.read()
                            logger.info(f"TOC图片加载成功，大小: {len(image_bytes)} bytes")
                        except Exception as e:
                            logger.error(f"TOC图片加载失败: {str(e)}")
                    else:
                        logger.warning(f"文件不存在: {image_path}")
                else:
                    # 从URL下载
                    image_bytes = self.download_image(toc_image_url)
                    if image_bytes:
                        logger.info(f"TOC图片下载成功，大小: {len(image_bytes)} bytes")

            # 发布推文
            post_uri = None
            if image_bytes:
                # 使用Image Embed（显示TOC图片）
                logger.info("发送推文（带TOC图片）")
                post_uri = self.bluesky_client.send_post_with_image(
                    text=post_text,
                    image_bytes=image_bytes,
                    image_alt="TOC Image",
                    facets=post_facets
                )
            else:
                # 使用External Embed（链接预览卡片）
                logger.info("发送推文（带链接预览卡片）")
                post_uri = self.bluesky_client.send_post(
                    text=post_text,
                    facets=post_facets,
                    external_url=doi_link
                )

            if not post_uri:
                logger.error("推文发布失败")
                return False

            # 更新Google Sheets记录
            send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if self.google_client.update_article_status(
                row_number=row_number,
                status="已发送",
                send_time=send_time,
                post_uri=post_uri
            ):
                logger.info(f"文章发布成功: {title}")
                return True
            else:
                logger.warning("推文发布成功，但Google Sheets记录更新失败")
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
        pending_articles = self.google_client.get_pending_articles()

        if not pending_articles:
            logger.info("没有未发送的文章")
            return True

        # 发布第一条文章
        article_data = pending_articles[0]

        # 获取行号（假设第一条未发送文章在所有记录中的位置）
        all_records = self.google_client.get_all_records()
        index = all_records.index(article_data)
        row_number = self.google_client.get_row_number_by_index(index)

        return self.post_article(article_data, row_number)

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
    google_credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    google_spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    # 检查必需的环境变量
    if not all([bluesky_handle, bluesky_password, google_spreadsheet_id]):
        logger.error("缺少必需的环境变量")
        logger.error("请设置: BLUESKY_HANDLE, BLUESKY_PASSWORD, GOOGLE_SPREADSHEET_ID")
        logger.error("可选: GOOGLE_CREDENTIALS_FILE (默认: credentials.json)")
        return

    # 检查credentials文件
    if not os.path.exists(google_credentials_file):
        logger.error(f"Google认证文件不存在: {google_credentials_file}")
        logger.error("请从Google Cloud Console下载服务账号JSON文件")
        return

    # 创建机器人实例
    bot = BlueskyBot(
        bluesky_handle=bluesky_handle,
        bluesky_password=bluesky_password,
        google_credentials_file=google_credentials_file,
        google_spreadsheet_id=google_spreadsheet_id
    )

    # 连接Google Sheets
    if not bot.google_client.connect():
        logger.error("连接Google Sheets失败")
        return

    # 启动定时任务
    bot.start_scheduler()

    # 持续运行
    bot.run_forever()


if __name__ == "__main__":
    main()
