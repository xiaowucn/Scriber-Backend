import random
from hashlib import md5
from io import BytesIO

import pytest
import yaml

from remarkable import base_handler
from remarkable.config import _config

test_config_patch = """web:
  plugins:
    - "ecitic"
client:
  name: "ecitic_poc"
ecitic:
  report_types:
    small_scattered:
      name: "“小而分散”类资产"
      molds:
        - "“小而分散”类资产"
    not_small_scattered:
      name: "非“小而分散”类资产"
      molds:
        - "非“小而分散”类资产"
"""

test_config = yaml.safe_load(BytesIO(test_config_patch.encode("utf8")))

@pytest.fixture(scope="module", autouse=True)
def mock_config():
    _config.merge(test_config)
    yield _config
    _config.reload()
    # with pytest.MonkeyPatch().context() as m:
    #     print("module_mock_config")
    #     get_config = mock_get_config(yaml.safe_load(BytesIO(test_config_patch.encode("utf8"))))
    #     m.setattr(base_handler.config, "get_config", get_config)


@pytest.mark.gen_test
async def test_ecitic_project_curd(login, module_http_client, pdf_file_bytes):
    login(base_handler.BaseHandler)

    # fetch report types
    rsp = await module_http_client.get("/plugins/ecitic/supported_report_types")

    assert rsp.status_code == 200
    report_types = rsp.json()["data"]

    assert report_types == test_config["ecitic"]["report_types"]

    # create project
    files = {"file": ("test.pdf", pdf_file_bytes, "application/pdf")}
    md5_hash = md5(pdf_file_bytes).hexdigest()
    project_meta = {"project_name": "hello kitty", "project_type": random.choice(list(report_types))}

    rsp = await module_http_client.post("plugins/ecitic/projects", data=project_meta, files=files)
    data = rsp.json()["data"]

    assert data["meta_info"]["project_name"] == project_meta["project_name"]
    assert data["hash"] == md5_hash

    # retrieve projects
    rsp = await module_http_client.get("/plugins/ecitic/projects")
    json_data = rsp.json()
    print("json_data", json_data)
    # file = json_data["data"]["items"][0]
    # assert file["meta_info"]["project_name"] == project_meta["project_name"]
    assert data["hash"] == md5_hash

    # delete project
    rsp = await module_http_client.delete(f"/plugins/ecitic/projects/{data['id']}")
    assert rsp.status_code == 200
