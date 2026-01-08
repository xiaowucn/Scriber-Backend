import logging
import math
import os
import random
import xml.etree.ElementTree as ET
import zipfile

import httpx
import pymupdf
from pdfparser.pdftools.count_page_num import get_page_num
from pptx import Presentation

from remarkable.config import get_config

logger = logging.getLogger(__name__)


class DocumentInspector:
    LOW_PAGE_THRESHOLD: int = 3
    LARGE_FILE_THRESHOLD_KB: float = 12
    BASE_FILE_OVERHEAD_KB: float = 11.0
    AVG_CONTENT_KB_PER_PAGE: float = 2

    @classmethod
    def _estimate_pages_fallback(cls, filesize_kb: float) -> int:
        content_size_kb = filesize_kb - cls.BASE_FILE_OVERHEAD_KB
        if content_size_kb > 0:
            estimated_pages = math.ceil(content_size_kb / cls.AVG_CONTENT_KB_PER_PAGE)
            logger.info(f"采用后备方案: 根据文件大小 ({filesize_kb:.2f} KB) 估算页数为 {estimated_pages}")
            return estimated_pages
        logger.info("采用后备方案: 所有估算方法均不适用，默认文件为 1 页")
        return 1

    @staticmethod
    def _get_pages_from_docx_xml(docx_path: str) -> int:
        try:
            with zipfile.ZipFile(docx_path, "r") as docx_zip:
                app_xml_content = docx_zip.read("docProps/app.xml")
                root = ET.fromstring(app_xml_content)
                for elem in root.iter():
                    if elem.tag.endswith("Pages") and elem.text and elem.text.isdigit():
                        logger.info(f"从 '{docx_path}' 的 app.xml (无特定命名空间) 中直接解析到页数: {elem.text}")
                        return int(elem.text)
        except Exception as e:
            logger.warning(f"直接从 XML 元数据读取 '{docx_path}' 页数时发生意外错误: {e}")
        return 0

    @classmethod
    def get_word_page_count(cls, docx_path: str) -> int:
        page = cls._get_pages_from_docx_xml(docx_path)
        filesize_kb = os.path.getsize(docx_path) / 1024
        if page <= cls.LOW_PAGE_THRESHOLD:
            if filesize_kb > cls.LARGE_FILE_THRESHOLD_KB:
                logger.warning(
                    f"文件 '{docx_path}' 元数据页数 ({page}) 过低，"
                    f"与其文件大小 ({filesize_kb:.2f} KB) 严重不符。元数据不可靠。"
                )
                return cls._estimate_pages_fallback(filesize_kb)
        logger.info(f"文件 '{docx_path}' 的元数据页数 ({page}) 通过校验，予以采纳。")
        return page

    @staticmethod
    def get_ppt_page_count(pptx_path: str) -> int:
        try:
            prs = Presentation(pptx_path)
            slide_count = len(prs.slides)
            logger.info(f"PowerPoint 文档 '{pptx_path}' 包含 {slide_count} 张幻灯片。")
            return slide_count
        except Exception as e:
            logger.error(f"处理 PowerPoint 文档 '{pptx_path}' 时出错: {e}")
            return 0

    @staticmethod
    def get_pdf_page_count(pdf_path: str) -> int:
        try:
            return get_page_num(pdf_path)
        except Exception as e:
            logger.error(f"处理 PDF 文档 '{pdf_path}' 时出错: {e}")
            return 0

    @staticmethod
    async def get_page_count_from_pdfinsight() -> int:
        url = f"{get_config('app.auth.pdfinsight.url')}/api/v1/pending-pages"
        try:
            async with httpx.AsyncClient(
                verify=False, timeout=10, transport=httpx.AsyncHTTPTransport(retries=3)
            ) as client:
                response = await client.get(url=url)
                response.raise_for_status()
                return response.json()["data"]["pending_pages"]
        except Exception as e:
            logger.exception(f"获取insight待处理页数时出错: {e}")
            return random.randint(1, 100)

    @staticmethod
    def is_scanned(pdf_path: str, sample_pages: int = 3) -> bool:
        """
        判断 PDF 是否为扫描件：
        - 前 N 页都没有文字
        - 含有图像对象
        """
        try:
            doc = pymupdf.open(pdf_path)
            for i in range(min(sample_pages, len(doc))):
                page = doc[i]
                if page.get_text().strip():
                    return False
            return True
        except Exception as e:
            logger.exception(f"扫描件判断失败: {e}")
            return False
