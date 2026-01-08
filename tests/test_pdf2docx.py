import json

import filetype

from remarkable.common.util import read_zip_first_file
from remarkable.service.pdf2docx import pdf2docx


def test_pdf2docx():
    interdoc = json.loads(read_zip_first_file('data/tests/pdf2docx_sample.zip'))
    kind = filetype.guess(pdf2docx(interdoc))
    assert kind and kind.extension == 'docx'
