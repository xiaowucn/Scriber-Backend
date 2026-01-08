from unittest.mock import Mock

import pytest
from pdfparser.pdftools.pdf_util import PDFUtil

from remarkable.common.storage import localstorage
from remarkable.models.new_file import NewFile
from remarkable.plugins.fileapi.worker import (
    PDFCache,
    optimize_outline,
)
from tests import DataInfo
from tests.helpers import sync_file_for_test


@pytest.fixture(scope="function")
def file_cache():
    args = (DataInfo.file_id, DataInfo.schema_id, False, DataInfo.sample_path, '', False)
    sync_file_for_test(args)

    file = Mock(NewFile)
    file.hash = DataInfo.hash
    file.id = 0
    file.pdfinsight_path.return_value = localstorage.get_path(DataInfo.pdfinsight)
    file.pdf_path.return_value = localstorage.get_path(DataInfo.hash)
    file.pdf_cache_path.return_value = localstorage.get_cache_path(DataInfo.hash)

    pdf_page_cache = PDFCache(file, None)
    pdf_page_cache.build(True)

    return pdf_page_cache


def test_pdf_cache(file_cache):
    for keyword in ['本次配股募集', '中国证监会', '700419', '募集资金用途', '交易安排\n']:
        find_res = file_cache.search(keyword)
        assert find_res
        get_text = PDFUtil.get_text_from_chars_with_white
        for res in find_res:
            for item in res['items']:
                for outline in item['outlines']:
                    box = {'box': outline, 'page': item['page']}
                    text, chars = file_cache.get_text_in_box(box, get_text)
                    box['box'] = optimize_outline(chars)
                    assert text == keyword

                    text, chars = file_cache.get_text_in_box(box, get_text)
                    assert text == keyword
