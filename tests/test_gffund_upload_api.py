from io import BytesIO

import pytest
import yaml

from remarkable import base_handler
from remarkable.common.storage import localstorage
from remarkable.config import project_root, _config
from remarkable.plugins.ext_api.gffund_handler_extension import GFFundUploadFile

test_config_patch = """web:
  plugins:
    - "fileapi"
    - "ext_api"
app:
  simple_token: "eyJzdWIiOiIxMjM"
"""

test_config = yaml.safe_load(BytesIO(test_config_patch.encode("utf8")))


@pytest.fixture(scope="module", autouse=True)
def mock_config():
    _config.merge(test_config)
    yield _config
    _config.reload()


@pytest.fixture(autouse=True)
def auto_login(login):
    login(base_handler.BaseHandler)


async def create_mold(data, client):
    return await client("/mold", json_data=data, api_version="")


class TestGFFundUploadApi:
    file_path = f"{project_root}/data/tests/gffund_test.tif"
    headers = {"Content-Type": "multipart/form-data", "access-token": "eyJzdWIiOiIxMjM"}
    url = "/external_api/v1/gffund/upload"
    files = {"file": ("gffund_test.tif", localstorage.read_file(file_path), "application/image")}

    async def import_fax(self, client):
        file_path = f"{project_root}/data/tests/gffund_fax.xlsx"
        url = "/external_api/v1/gffund/fax"
        files = {"fax_file": ("gffund_fax.xlsx", localstorage.read_file(file_path))}
        return await client.post(url, files=files, headers=self.headers, api_version="")

    @pytest.mark.gen_test
    async def test_upload_file(self, module_http_client, monkeypatch):
        rsp = await self.import_fax(module_http_client)
        assert rsp.status_code == 200

        items = {
            "business_mold": {
                "id": None,
                "data": {
                    "name": "广发业务申请表模板",
                    "mold_type": 0,
                    "data": {"schemas": [{"name": "广发业务申请表模板", "schema": {}}], "schema_types": []},
                },
                "items": [
                    {"fax_subject": "ny-wuq@crctrust.com", "file_id": "110"},
                    {"file_id": "112"},
                ]
            },
            "other_mold": {
                "id": None,
                "data": {
                    "name": "广发业务申请表其他模板",
                    "mold_type": 0,
                    "data": {"schemas": [{"name": "广发业务申请表其他模板", "schema": {}}], "schema_types": []},
                }
            },
            "a_mold": {
                "id": None,
                "data": {
                    "name": "广发业务申请表A",
                    "mold_type": 0,
                    "data": {"schemas": [{"name": "广发业务申请表A", "schema": {}}], "schema_types": []},
                },
                "items": [
                    {"fax_number": "87553363", "file_id": "112"}
                ]
            }
        }

        monkeypatch.setattr(GFFundUploadFile, "_get_image_parts_text", lambda x: "基金其他")

        for name, value in items.items():
            rsp = await module_http_client.post("/mold", json_data=value["data"])
            assert rsp.status_code == 200

            mold_id = module_http_client.get_data(rsp, "id")
            value["id"] = module_http_client.get_data(rsp, "id")

            for item in value.get("items", []):
                rsp = await module_http_client.post(self.url, files=self.files, data=item, headers=self.headers,
                                                    api_version="")
                assert rsp.status_code == 200

                data = module_http_client.get_data(rsp)[0]

                file_id = data["id"]
                rsp = await module_http_client.get(f'/plugins/fileapi/file/search?fileid={file_id}')
                file = module_http_client.get_data(rsp, "items")[0]

                assert file["user_name"] == "admin"
                assert file["id"] == int(file_id)
                assert file["molds"][0] == mold_id
                assert file["meta_info"]["gffund_file_id"] == data["gffund_file_id"]
