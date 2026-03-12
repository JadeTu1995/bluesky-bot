"""
Bluesky API 封装工具
提供认证、图片上传、发布推文等功能
"""

import logging
from typing import Optional
from atproto import Client

logger = logging.getLogger(__name__)


class BlueskyClient:
    """Bluesky客户端封装"""

    def __init__(self, handle: str, password: str):
        """
        初始化Bluesky客户端

        Args:
            handle: Bluesky账号 (用户名或邮箱)
            password: Bluesky密码 (建议使用应用密码)
        """
        self.handle = handle
        self.password = password
        self.client = Client()
        self._profile = None

    def login(self) -> bool:
        """
        登录Bluesky

        Returns:
            bool: 登录是否成功
        """
        try:
            self._profile = self.client.login(
                login=self.handle,
                password=self.password
            )
            logger.info(f"Bluesky登录成功: {self._profile.handle}")
            return True
        except Exception as e:
            logger.error(f"Bluesky登录失败: {str(e)}")
            return False

    def send_post_with_image(
        self,
        text: str,
        image_bytes: bytes,
        image_alt: str = "TOC Image",
        facets: list = None
    ) -> Optional[str]:
        """
        发布带图片的推文

        注意：Bluesky限制一条推文只能有一个embed，因此有图片时无法同时显示链接预览卡片。

        Args:
            text: 推文文本
            image_bytes: 图片二进制数据
            image_alt: 图片alt文本
            facets: rich text facets（用于创建链接等）

        Returns:
            Optional[str]: 推文URI，失败返回None
        """
        try:
            from datetime import datetime, timezone

            # 先上传图片
            image_upload = self.client.upload_blob(image_bytes)

            # 创建图片嵌入 - 直接传递blob对象
            embed = {
                "$type": "app.bsky.embed.images",
                "images": [
                    {
                        "alt": image_alt,
                        "image": image_upload.blob
                    }
                ]
            }

            # 生成创建时间（ISO 8601格式，UTC时区）
            created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            # 发送推文，包含图片和facets
            # 注意：Bluesky不能同时有图片embed和external embed
            record_data = {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": created_at,
                "embed": embed
            }
            if facets:
                record_data["facets"] = facets

            response = self.client.com.atproto.repo.create_record(
                {
                    "collection": "app.bsky.feed.post",
                    "repo": self.client.me.did,
                    "record": record_data
                }
            )

            post_uri = response.uri
            logger.info(f"推文发布成功: {post_uri}")
            return post_uri
        except Exception as e:
            logger.error(f"推文发布失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def send_post(self, text: str, facets: list = None, external_url: str = None) -> Optional[str]:
        """
        发布推文，支持链接预览卡片

        Args:
            text: 推文文本
            facets: rich text facets（用于创建链接等）
            external_url: 外部链接URL（用于生成预览卡片）

        Returns:
            Optional[str]: 推文URI，失败返回None
        """
        try:
            from datetime import datetime, timezone

            # 如果有external_url，创建external embed
            embed = None
            if external_url:
                embed = {
                    "$type": "app.bsky.embed.external",
                    "external": {
                        "uri": external_url,
                        "title": "",
                        "description": "",
                    }
                }
                logger.info(f"创建External Embed，URL: {external_url}")

            # 生成创建时间（ISO 8601格式，UTC时区）
            created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

            # 尝试使用facets参数
            if facets or embed:
                record_data = {
                    "$type": "app.bsky.feed.post",
                    "text": text,
                    "createdAt": created_at,
                }
                if facets:
                    record_data["facets"] = facets
                if embed:
                    record_data["embed"] = embed

                response = self.client.com.atproto.repo.create_record(
                    {
                        "collection": "app.bsky.feed.post",
                        "repo": self.client.me.did,
                        "record": record_data
                    }
                )
            else:
                response = self.client.send_post(text=text)
            post_uri = response.uri
            logger.info(f"推文发布成功: {post_uri}")
            return post_uri
        except Exception as e:
            logger.error(f"推文发布失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def delete_post(self, post_uri: str) -> bool:
        """
        删除推文

        Args:
            post_uri: 推文URI

        Returns:
            bool: 删除是否成功
        """
        try:
            result = self.client.delete_post(post_uri=post_uri)
            logger.info(f"推文删除成功: {post_uri}")
            return result
        except Exception as e:
            logger.error(f"推文删除失败: {str(e)}")
            return False


def create_bluesky_post_text(title: str, doi_link: str) -> str:
    """
    创建Bluesky推文文本

    Args:
        title: 文章标题
        doi_link: DOI链接

    Returns:
        str: 推文文本
    """
    # Bluesky会自动识别URL为可点击的链接
    return f"{title}\n\nDOI: {doi_link}"


def create_post_facets(text: str, doi_link: str) -> list:
    """
    创建推文的facets（rich text features），用于明确标记URL为可点击链接

    Args:
        text: 推文文本
        doi_link: DOI链接

    Returns:
        list: facets列表
    """
    import re

    # 查找DOI链接在文本中的位置
    # 查找 "DOI: " 后面的URL
    pattern = r'DOI:\s*(https?://[^\s]+)'
    match = re.search(pattern, text)

    if not match:
        return []

    # 获取URL的起始和结束位置
    uri_start = match.start(1)
    uri_end = match.end(1)

    # 创建facet
    facet = {
        "$type": "app.bsky.richtext.facet",
        "features": [
            {
                "$type": "app.bsky.richtext.facet#link",
                "uri": doi_link
            }
        ],
        "index": {
            "byteStart": uri_start,
            "byteEnd": uri_end
        }
    }

    return [facet]
