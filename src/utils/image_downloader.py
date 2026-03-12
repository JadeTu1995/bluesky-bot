"""
图片下载工具
"""


def download_image(url: str, timeout: int = 30) -> tuple:
    """
    下载图片，添加浏览器请求头以绕过防盗链

    Args:
        url: 图片URL
        timeout: 超时时间（秒）

    Returns:
        tuple: (image_bytes, content_type, error_message)
    """
    import requests

    # 添加浏览器请求头，模拟真实浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)

        if response.status_code == 200:
            image_bytes = response.content
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            return image_bytes, content_type, None
        else:
            return None, None, f"HTTP {response.status_code}"

    except requests.exceptions.Timeout:
        return None, None, "下载超时"
    except requests.exceptions.RequestException as e:
        return None, None, str(e)
    except Exception as e:
        return None, None, f"未知错误: {str(e)}"


def is_valid_image_url(url: str) -> bool:
    """
    检查URL是否是有效的图片URL

    Args:
        url: 图片URL

    Returns:
        bool: 是否有效
    """
    if not url or not url.strip():
        return False

    # 检查是否以http开头
    if not url.startswith(('http://', 'https://')):
        return False

    # 检查是否包含图片扩展名（可选，有些图片URL没有扩展名）
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg']
    has_extension = any(url.lower().endswith(ext) for ext in image_extensions)

    return True  # 允许没有扩展名的URL（API动态生成的图片）
