import json
from pathlib import Path

project_root = Path(__file__).parent.parent

def compare_json(json_a, json_b):
    str_a = json.dumps(json_a, sort_keys=True, ensure_ascii=False)
    str_b = json.dumps(json_b, sort_keys=True, ensure_ascii=False)
    assert str_a == str_b


class DataInfo:
    sample_path = f"{project_root}/data/tests/sample.zip"
    schema_id = 220
    vid = 0
    file_id = 10194
    qid = 9625
    hash = '6c40b874bd5f95147ba47699b8cd7134'
    pdfinsight = 'c82b512e1616beb2f2f08d314ee6a1b9'


class ZJHDataInfo:
    sample_path = f"{project_root}/data/tests/zjh_2124.zip"
    schema_id = 3
    vid = 0
    file_id = 2124
    qid = 12881


class SSEDataInfo:
    sample_path = f"{project_root}/data/tests/sse_2162.zip"
    schema_id = 2
    file_id = 2162
    qid = 13362


TestFilePath = f"{project_root}/data/tests/TestFile.pdf"
