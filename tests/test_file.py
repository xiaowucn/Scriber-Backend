import os.path
from unittest.mock import AsyncMock

import pytest

from remarkable.common.util import read_zip_first_file
from remarkable.service.new_file import octopus_html2pdf


@pytest.mark.asyncio(loop_scope="module")
async def test_octopus_html2pdf(project_root, monkeypatch):
    zip_path = os.path.join(project_root, "data", "tests", "test_octopus_html2pdf.zip")
    with monkeypatch.context() as m:
        post_mock = AsyncMock(return_value="body")
        m.setattr("remarkable.service.new_file.html2pdf", post_mock)

        title, body = await octopus_html2pdf(read_zip_first_file(zip_path))
        assert title == "关于2021年记账式附息（十六期）国债发行工作有关事宜的通知.pdf"
        assert body == "body"
        # kind = filetype.guess(body)
        # assert kind and kind.extension == "pdf"
