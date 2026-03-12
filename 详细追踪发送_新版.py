"""
详细追踪发送过程，每一步都显示详细信息（不发送TOC图片，只显示链接预览）
"""
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from dotenv import load_dotenv
load_dotenv()

print("=" * 70)
print("📋 步骤1：读取未发送文章")
print("=" * 70)
print()

from tools.google_sheets_tool import GoogleSheetsClient

client = GoogleSheetsClient(
    os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
    os.getenv("GOOGLE_SPREADSHEET_ID")
)

client.connect()
all_records = client.get_all_records()

# 找到第一条未发送的文章
article = None
for record in all_records:
    status = record.get('发送状态', '').strip()
    if status == '未发送':
        article = record
        break

if not article:
    print("❌ 没有找到未发送的文章")
    input("\n按回车退出...")
    sys.exit(1)

print(f"✅ 找到未发送文章")
print(f"   标题: '{article.get('标题', '')}'")
print(f"   DOI: '{article.get('DOI链接', '')}'")
print(f"   TOC图片: '{article.get('TOC图片', '')}'")
print()

row_number = client.get_row_number_by_index(all_records.index(article))
print(f"   行号: {row_number}")
print()

print("=" * 70)
print("📝 步骤2：生成推文内容")
print("=" * 70)
print()

title = article.get('标题', '')
doi_link = article.get('DOI链接', '')

if not title:
    print("❌ 标题为空")
    input("\n按回车退出...")
    sys.exit(1)

from utils.post_utils import create_post_with_facets
post_text, post_facets = create_post_with_facets(title, doi_link)

print(f"✅ 推文内容:")
print(f"   {post_text}")
print(f"   长度: {len(post_text)} 字符")
print(f"   Facets: {len(post_facets)} 个")
print()

print("=" * 70)
print("📱 步骤3：登录Bluesky")
print("=" * 70)
print()

bluesky_handle = os.getenv("BLUESKY_HANDLE")
bluesky_password = os.getenv("BLUESKY_PASSWORD")

print(f"   账号: {bluesky_handle}")
print(f"   密码: {'*' * len(bluesky_password)}")
print()

from tools.bluesky_tool import BlueskyClient

bluesky_client = BlueskyClient(
    handle=bluesky_handle,
    password=bluesky_password
)

if not bluesky_client.login():
    print("❌ Bluesky登录失败")
    print()
    print("可能的原因:")
    print("1. 账号或密码错误")
    print("2. 网络连接问题")
    print("3. Bluesky服务暂时不可用")
    input("\n按回车退出...")
    sys.exit(1)

print(f"✅ Bluesky登录成功")
print(f"   账号: {bluesky_client._profile.handle}")
print()

print("=" * 70)
print("🖼️  步骤4：准备TOC图片")
print("=" * 70)
print()

toc_image_url = article.get('TOC图片', '').strip()
image_bytes = None

# 优先从assets目录读取
if toc_image_url:
    # 检查是否是文件名（不是URL）
    if not toc_image_url.startswith('http'):
        # 从assets目录读取
        image_path = os.path.join('assets', toc_image_url)
        print(f"从assets目录读取图片: {image_path}")

        if os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                print(f"✅ 图片加载成功")
                print(f"   大小: {len(image_bytes)} bytes")
            except Exception as e:
                print(f"❌ 图片加载失败: {str(e)}")
        else:
            print(f"❌ 文件不存在: {image_path}")
    else:
        # 从URL下载
        print(f"从URL下载图片: {toc_image_url}")
        print("正在下载图片...")

        try:
            import requests

            # 添加浏览器请求头，绕过防盗链
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(toc_image_url, headers=headers, timeout=30)
            response.raise_for_status()

            image_bytes = response.content
            print(f"✅ 图片下载成功")
            print(f"   大小: {len(image_bytes)} bytes")
        except Exception as e:
            print(f"❌ 图片下载失败: {str(e)}")

# 如果没有图片，询问用户
if not image_bytes:
    print()
    print("=" * 70)
    print("📥 步骤4.5：手动选择TOC图片（可选）")
    print("=" * 70)
    print()
    print("您可以选择：")
    print("1. 不使用图片（只发送链接预览卡片）")
    print("2. 输入图片文件名（从assets目录读取）")
    print()

    choice = input("请选择（1/2，默认1）: ").strip() or "1"

    if choice == "2":
        image_filename = input("请输入图片文件名（例如：toc.jpg）: ").strip()

        if image_filename:
            image_path = os.path.join('assets', image_filename)
            print(f"从assets目录读取图片: {image_path}")

            if os.path.exists(image_path):
                try:
                    with open(image_path, 'rb') as f:
                        image_bytes = f.read()
                    print(f"✅ 图片加载成功")
                    print(f"   大小: {len(image_bytes)} bytes")
                except Exception as e:
                    print(f"❌ 图片加载失败: {str(e)}")
            else:
                print(f"❌ 文件不存在: {image_path}")
    else:
        print("ℹ️  将使用不带图片的链接预览卡片")

print()

print("=" * 70)
print("🚀 步骤5：发送推文")
print("=" * 70)
print()

post_uri = None
try:
    if image_bytes:
        print("正在发送推文（带TOC图片）...")
        post_uri = bluesky_client.send_post_with_image(
            text=post_text,
            image_bytes=image_bytes,
            image_alt="TOC Image",
            facets=post_facets
        )
    else:
        print("正在发送推文（带链接预览卡片）...")
        post_uri = bluesky_client.send_post(
            text=post_text,
            facets=post_facets,
            external_url=doi_link
        )

    if post_uri:
        print(f"✅ 推文发送成功")
        print(f"   推文URI: {post_uri}")
    else:
        print(f"❌ 推文发送失败")
except Exception as e:
    print(f"❌ 发送失败: {str(e)}")
    import traceback
    traceback.print_exc()
    input("\n按回车退出...")
    sys.exit(1)

print()

print("=" * 70)
print("💾 步骤6：更新Google Sheets状态")
print("=" * 70)
print()

from datetime import datetime
send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

try:
    success = client.update_article_status(
        row_number=row_number,
        status="已发送",
        send_time=send_time,
        post_uri=post_uri
    )

    if success:
        print(f"✅ 状态更新成功")
        print(f"   行号: {row_number}")
        print(f"   发送状态: 已发送")
        print(f"   发送时间: {send_time}")
        print(f"   推文URI: {post_uri}")
    else:
        print(f"❌ 状态更新失败")
except Exception as e:
    print(f"❌ 状态更新错误: {str(e)}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("✅ 全部完成！")
print("=" * 70)
print()
print("💡 推文效果:")
if image_bytes:
    print("   1. 文章标题")
    print("   2. DOI可点击链接（蓝色、带下划线）")
    print("   3. TOC图片（显示在推文中）")
else:
    print("   1. 文章标题")
    print("   2. DOI可点击链接（蓝色、带下划线）")
    print("   3. 链接预览卡片（如果Bluesky能抓取）")

input("\n按回车退出...")
