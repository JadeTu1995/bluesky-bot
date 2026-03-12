"""
推文生成工具
"""


def create_post_with_facets(title: str, doi_link: str):
    """
    创建推文文本和facets

    Args:
        title: 文章标题
        doi_link: DOI链接

    Returns:
        tuple: (text, facets)
    """
    # 生成推文文本（标题和DOI之间只有一个换行）
    text = f"{title}\nDOI: {doi_link}"

    # 生成facets（用于明确标记DOI链接为可点击）
    facets = []
    if doi_link:
        import re

        # 查找DOI链接在文本中的位置
        pattern = r'DOI:\s*(https?://[^\s]+)'
        match = re.search(pattern, text)

        if match:
            # 获取URL的起始和结束位置（字节位置）
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

            facets.append(facet)

    return text, facets
