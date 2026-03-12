"""
Google Sheets 工具模块
用于读取和更新Google Sheets表格数据
"""

import logging
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)


class GoogleSheetsClient:
    """Google Sheets客户端封装"""

    def __init__(self, credentials_file: str, spreadsheet_id: str):
        """
        初始化Google Sheets客户端

        Args:
            credentials_file: Google Cloud服务账号JSON文件路径
            spreadsheet_id: Google表格ID（从URL中获取）
        """
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.sheet = None
        self.worksheet = None

    def connect(self) -> bool:
        """
        连接到Google Sheets

        Returns:
            bool: 连接是否成功
        """
        try:
            # 加载认证信息
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            credentials = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=scope
            )

            # 创建客户端
            self.client = gspread.authorize(credentials)

            # 打开表格
            self.sheet = self.client.open_by_key(self.spreadsheet_id)

            # 获取第一个工作表
            self.worksheet = self.sheet.sheet1

            logger.info(f"成功连接到Google Sheets: {self.sheet.title}")
            return True

        except Exception as e:
            logger.error(f"连接Google Sheets失败: {str(e)}")
            return False

    def get_all_records(self) -> List[Dict[str, Any]]:
        """
        获取所有记录

        Returns:
            List[Dict[str, Any]]: 记录列表
        """
        try:
            if not self.worksheet:
                raise Exception("未连接到Google Sheets")

            # 使用 get_all_values() 而不是 get_all_records()
            # 因为 get_all_records() 在处理列标题时可能有问题
            all_values = self.worksheet.get_all_values()

            if not all_values or len(all_values) < 2:
                logger.warning("表格为空或只有标题行")
                return []

            # 第一行是标题
            headers = all_values[0]

            # 将数据行转换为字典
            records = []
            for row in all_values[1:]:
                # 确保行数据长度和标题长度一致
                if len(row) < len(headers):
                    row = row + [''] * (len(headers) - len(row))

                record = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        record[header] = row[i]
                    else:
                        record[header] = ''

                records.append(record)

            logger.info(f"获取到 {len(records)} 条记录")
            return records

        except Exception as e:
            logger.error(f"获取记录失败: {str(e)}")
            return []

    def get_pending_articles(self) -> List[Dict[str, Any]]:
        """
        获取未发送的文章

        Returns:
            List[Dict[str, Any]]: 未发送的文章列表
        """
        try:
            all_records = self.get_all_records()

            # 筛选"发送状态"为"未发送"的文章
            pending = [
                record for record in all_records
                if record.get("发送状态") == "未发送"
            ]

            logger.info(f"找到 {len(pending)} 条未发送文章")
            return pending

        except Exception as e:
            logger.error(f"获取未发送文章失败: {str(e)}")
            return []

    def update_article_status(
        self,
        row_number: int,
        status: str,
        send_time: str,
        post_uri: str
    ) -> bool:
        """
        更新文章状态

        Args:
            row_number: 行号（从2开始，因为第1行是标题）
            status: 发送状态（"已发送"或"未发送"）
            send_time: 发送时间
            post_uri: Bluesky推文URI

        Returns:
            bool: 更新是否成功
        """
        try:
            if not self.worksheet:
                raise Exception("未连接到Google Sheets")

            # 获取列索引
            header = self.worksheet.row_values(1)
            status_col = header.index("发送状态") + 1
            time_col = header.index("发送时间") + 1
            uri_col = header.index("Bluesky推文URI") + 1

            # 更新单元格
            self.worksheet.update_cell(row_number, status_col, status)
            self.worksheet.update_cell(row_number, time_col, send_time)
            self.worksheet.update_cell(row_number, uri_col, post_uri)

            logger.info(f"成功更新第 {row_number} 行记录")
            return True

        except Exception as e:
            logger.error(f"更新记录失败: {str(e)}")
            return False

    def add_article(
        self,
        title: str,
        doi_link: str,
        toc_image_url: str = ""
    ) -> bool:
        """
        添加新文章

        Args:
            title: 文章标题
            doi_link: DOI链接
            toc_image_url: TOC图片URL（可选）

        Returns:
            bool: 添加是否成功
        """
        try:
            if not self.worksheet:
                raise Exception("未连接到Google Sheets")

            # 添加新行
            row_data = [
                title,
                doi_link,
                toc_image_url,
                "未发送",
                "",
                ""
            ]

            self.worksheet.append_row(row_data)

            logger.info(f"成功添加文章: {title}")
            return True

        except Exception as e:
            logger.error(f"添加文章失败: {str(e)}")
            return False

    def get_row_number_by_index(self, index: int) -> int:
        """
        根据记录索引获取行号（记录索引从0开始，行号从2开始）

        Args:
            index: 记录索引

        Returns:
            int: 行号
        """
        return index + 2  # 第1行是标题行
