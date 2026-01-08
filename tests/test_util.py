import os
from pathlib import Path

import pytest

from remarkable.common.util import excel_row_iter, simple_match_ext
from remarkable.config import project_root


@pytest.mark.parametrize(
    "path",
    [
        Path(os.path.join(project_root, "data", "tests", p))
        for p in (
            "ms_03.xls",
            "ms_07.xlsx",
            "sample.png",
            "TestFile.pdf",
            "test_octopus_html2pdf.zip",
            "strange_pdf.pdf",
            "ms-CDFV2.doc",
        )
    ],
)
def test_match_ext(path):
    from remarkable.common.util import match_ext

    assert simple_match_ext(path.suffix, path, path.suffix)
    assert match_ext(path.read_bytes(), path.suffix)


def test_excel_row_iter():
    test_paths = [os.path.join(project_root, "data", "tests", p) for p in ("ms_03.xls", "ms_07.xlsx")]
    for path in test_paths:
        for idx, row in enumerate(excel_row_iter(path, values_only=True), start=1):
            assert int(row[0]) == idx

        for row in excel_row_iter(path, skip_rows=4, sheet_index=1):
            assert int(row[0].value) == 1


def test_which_type():
    from concurrent.futures import ThreadPoolExecutor

    from remarkable.converter.ecitic.util import DocType

    cases = [
        ("关于xxx三六零小贷第1期资产支持专项计划的公告", DocType.MICRO_FINANCE),
        ("关于xxx360小贷第1期资产支持专项计划的公告", DocType.MICRO_FINANCE),
        ("关于xxx360数科第1期资产支持专项计划的公告", DocType.MICRO_FINANCE),
        ("关于xxx博远1号第2期资产支持专项计划的公告", DocType.MICRO_FINANCE),
        ("关于xxx荟享1号第2期资产支持专项计划的公告", DocType.MICRO_FINANCE),
        ("关于xxx耘睿1号第2期资产支持专项计划的公告", DocType.MICRO_FINANCE),
        ("关于xxx东道第2期资产支持专项计划的公告", DocType.RECEIVABLE_ACCOUNTS),
        ("关于xxx博远1号第1期资产支持专项计划的公告", DocType.RECEIVABLE_ACCOUNTS),
        ("关于xxx博远2号第3期资产支持专项计划的公告", DocType.RECEIVABLE_ACCOUNTS),
        ("关于xxx博远2号第三期资产支持专项计划的公告", DocType.RECEIVABLE_ACCOUNTS),
        ("关于xxx禾昱资产支持专项计划的公告", DocType.RECEIVABLE_ACCOUNTS),
    ]
    with ThreadPoolExecutor(max_workers=len(cases)) as executor:
        for text, expected in cases:
            future = executor.submit(DocType.which_type, text)
            assert future.result() == expected
