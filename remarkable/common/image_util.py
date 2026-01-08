import base64
import logging
from io import BytesIO

from pdfparser.pdftools.pdfium_util import PDFiumUtil
from PIL import Image


def image_to_base64(image, img_format="JPEG"):
    output_buffer = BytesIO()
    image.save(output_buffer, format=img_format)
    byte_data = output_buffer.getvalue()
    base64_str = str(base64.b64encode(byte_data), encoding="utf-8")
    return base64_str


def base64_to_image(base64_str, image_path=None):
    # base64_data = re.sub('^data:image/.+;base64,', '', base64_str)
    byte_data = base64.b64decode(base64_str)
    image_data = BytesIO(byte_data)
    img = Image.open(image_data)
    if image_path:
        img.save(image_path)
    return img


def outline_base64_str(pdf_path, page_index, outline, scale=1.0):
    page_img, base64_str = None, ""
    left, top, right, bottom = outline
    if left == right or top == bottom:
        return base64_str
    try:
        page_img = PDFiumUtil.get_page_bitmap(pdf_path, page_index, scale=scale)  # pdf页面
    except Exception:
        logging.exception("get_page_bitmap error: %s", pdf_path)
    if page_img:
        right = page_img.width if right > page_img.width else right
        bottom = page_img.width if bottom > page_img.height else bottom
        region_img = page_img.crop((left, top, right, bottom))  # 截图
        img_format = page_img.format or "JPEG"
        base64_str = image_to_base64(region_img, img_format)
    return base64_str
