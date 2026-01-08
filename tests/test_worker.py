import os.path
import tempfile
from functools import partial
from unittest import mock

import filetype
import pytest
from pdfparser.pdftools.pdf_doc import PDFDoc

from remarkable.config import project_root
from remarkable.models.new_file import NewFile
from remarkable.plugins.fileapi.worker import create_pdf
from remarkable.service.word import text2pdf


def mock_path_func(pdf_path, col="hash", **kwargs):
    if col == "hash":
        return os.path.join(project_root, "data/tests/sample.png")
    if col == "pdf":
        return pdf_path


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("PDFPARSER_CONFIG_OCR_PAI_CACHE", "true")
    monkeypatch.setenv("PDFPARSER_CONFIG_RPC_CLIENT_PAI_TARGET", "100.64.0.15:1889")


def _is_pdf(path):
    kind = filetype.guess(path)
    return kind and kind.extension == "pdf"


@pytest.mark.asyncio(loop_scope="session")
async def test_create_pdf(mock_env):
    file = NewFile(name="sample.png")
    with tempfile.NamedTemporaryFile() as pdf_path:
        with mock.patch.object(file, "path", partial(mock_path_func, pdf_path.name)):
            await create_pdf(file)
            assert _is_pdf(pdf_path.name)
        with tempfile.NamedTemporaryFile() as tmp_path:
            test_str = "hello♀♂出 1e"
            with open(tmp_path.name, "w") as in_fp:
                in_fp.write(f"{test_str}")
            await text2pdf(tmp_path.name, pdf_path.name)
            assert _is_pdf(pdf_path.name) and PDFDoc(pdf_path.name).pages[0]["texts"][0]["text"] == test_str
