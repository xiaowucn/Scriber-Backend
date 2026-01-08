from unittest import mock
from unittest.mock import patch

import pytest

from remarkable import base_handler
from remarkable.pw_models.model import MoldWithFK
from tests.utils import mock_get_config

test_config_patch = """web:
  plugins:
    - "fileapi"
    - "ccxi"
    - "ext_api"
"""

mocked_get_config = mock.Mock(side_effect=mock_get_config({
    "web": {
        "user_system_provider": "trident"
    }
}))

@pytest.fixture(autouse=True)
def auto_login(login):
    login(base_handler.BaseHandler)

@pytest.mark.gen_test
@patch("remarkable.models.new_user.get_config", mocked_get_config)
async def test_mold_crud(http_client):
    # create
    mold_data = {
        "name": "test",
        "mold_type": 0,
        "data": {"schemas": [{"name": "全称", "schema": {}}], "schema_types": []},
    }
    rsp = await http_client.post("/mold", json_data=mold_data)
    assert rsp.status_code == 200

    mold_id = http_client.get_data(rsp, "id")

    # tolerate_schema_ids
    with pytest.raises(AssertionError) as exp:
        await MoldWithFK.tolerate_schema_ids(9527)
        assert str(exp.value).endswith("not found")
        await MoldWithFK.tolerate_schema_ids("我的滑板鞋🛹")
        assert str(exp.value).endswith("not found")

    assert (await MoldWithFK.tolerate_schema_ids(mold_id)) == [mold_id]
    assert (await MoldWithFK.tolerate_schema_ids("test")) == [mold_id]

    # update
    update_mold = {
        "name": "updated_mold",
        "data": {
            "schemas": [{"name": "全称1", "schema": {}}],
            "schema_types": [],
        },
        "predictors": [{}],
    }
    rsp = await http_client.put(f"/mold/{mold_id}", json_data=update_mold)
    assert rsp.status_code == 200
    assert http_client.get_data(rsp, "name") == update_mold["name"]

    # retrieve
    rsp = await http_client.get(f"/mold/{mold_id}")
    assert rsp.status_code == 200

    # fetch all
    rsp = await http_client.get("/mold")
    assert rsp.status_code == 200

    # fetch all with specific fields
    rsp = await http_client.get("/mold?fields=name")
    assert rsp.status_code == 200
    items = http_client.get_data(rsp, "items")
    assert items and all("id" not in item and "name" in item for item in items)

    # delete
    rsp = await http_client.delete(f"/mold/{mold_id}")
    assert rsp.status_code == 200


@pytest.mark.gen_test
async def test_file_crud(http_client, pdf_file_bytes):
    new_project = {"name": "test_project", "default_molds": [], "is_public": 1}
    rsp = await http_client.post(f"/plugins/fileapi/project", json_data=new_project)

    assert rsp.status_code == 200

    data = http_client.get_data(rsp)
    pid, rtree_id = data["id"],  data["rtree_id"]

    rsp = await http_client.get(f"plugins/fileapi/project/{pid}")
    assert rsp.status_code == 200

    rsp = await http_client.get("/plugins/fileapi/project")
    assert rsp.status_code == 200

    update_project = {"name": "updated_project"}
    rsp = await http_client.put(f"/plugins/fileapi/project/{pid}", json_data=update_project)
    assert rsp.status_code == 200

    assert http_client.get_data(rsp, "name") == "updated_project"

    file_tree_name = "test_file_tree"
    rsp = await http_client.get(f"/plugins/fileapi/tree/{rtree_id}/name/{file_tree_name}")
    assert rsp.status_code == 200

    new_file_tree = {"name": file_tree_name}
    rsp = await http_client.post(f"/plugins/fileapi/tree/{rtree_id}/tree", json_data=new_file_tree)

    tree_id = http_client.get_data(rsp, "id")

    assert rsp.status_code == 200

    update_file_tree = {"name": "updated_file_tree"}
    rsp = await http_client.put(f"/plugins/fileapi/tree/{tree_id}", json_data=update_file_tree)
    assert http_client.get_data(rsp, "name") == update_file_tree["name"]

    # retrieve file_tree
    rsp = await http_client.get(f"/plugins/fileapi/tree/{rtree_id}?page=1")
    assert rsp.status_code == 200

    files = {"file": ("test.pdf", pdf_file_bytes, "application/pdf")}
    rsp = await http_client.post(f"/plugins/fileapi/tree/{tree_id}/file", files=files)
    fid = http_client.get_data(rsp)[0]["id"]

    update_file = {"name": "Test.pdf", "molds": []}
    rsp = await http_client.put(f"/plugins/fileapi/file/{fid}", json_data=update_file)
    assert rsp.status_code == 200

    rsp = await http_client.get(f"/plugins/fileapi/tree/{tree_id}")
    assert rsp.status_code == 200

    rsp = await http_client.get(f"/plugins/fileapi/file/search?fileid={fid}")
    file = http_client.get_data(rsp, "items")[0]
    assert file["name"] == update_file["name"]
    assert file["user_name"] == "admin"

    # delete file
    rsp = await http_client.delete(f"/plugins/fileapi/file/{fid}")
    assert rsp.status_code == 200

    # delete file_tree
    rsp = await http_client.delete(f"/plugins/fileapi/tree/{tree_id}")
    assert rsp.status_code == 200

    # delete file_project
    rsp = await http_client.delete(f"/plugins/fileapi/project/{pid}")
    assert rsp.status_code == 200

# @mark.skip("TODO: 拆分")
# class TestFileApi(BaseTestCase):
#     def setUp(self, **kwargs):
#         super(TestFileApi, self).setUp(yaml.safe_load(BytesIO(test_config_patch.encode("utf8"))))
#
#     def test_file_crud(self):
#         self.external_file_upload()
#         self.tag_crud()
#         self.ccxi_file_tag_crud()
#         self.question()
#         self.tag_delete()
#
#     def tag_crud(self):
#         # create
#         tag_data = {"name": "test_tag", "tag_type": 1}
#         rsp = self.post("/plugins/fileapi/tag", json_data=tag_data)
#         assert_status_ok(rsp)
#         self.tag_id = get_from_rsp(rsp, "id")
#
#         # update
#         update_tag = {"name": "updated_tag", "tag_type": 1}
#         rsp = self.put(f"/plugins/fileapi/tag/{self.tag_id}", json_data=update_tag)
#         assert_status_ok(rsp)
#         assert get_from_rsp(rsp, "name") == update_tag["name"]
#
#         # fetch all
#         rsp = self.get("/plugins/fileapi/tag")
#         assert_status_ok(rsp)
#
#     def tag_delete(self):
#         rsp = self.delete(f"/plugins/fileapi/tag/{self.tag_id}")
#         assert_status_ok(rsp)
#
#     def ccxi_file_tag_crud(self):
#         # create
#         tag_data = {"name": "ccx_tag", "molds": [self.mold_id]}
#         rsp = self.post("/plugins/ccxi/tags", json_data=tag_data)
#         assert_status_ok(rsp)
#         self.ccx_file_tag_id = get_from_rsp(rsp, "id")
#
#         # update
#         update_tag = {"name": "updated_ccx_tag", "molds": [self.mold_id]}
#         rsp = self.put(f"/plugins/ccxi/tag/{self.ccx_file_tag_id}", json_data=update_tag)
#         assert_status_ok(rsp)
#         assert get_from_rsp(rsp, "name") == update_tag["name"]
#
#         # retrieve
#         rsp = self.get(f"/plugins/ccxi/tag/{self.ccx_file_tag_id}")
#         assert_status_ok(rsp)
#         assert get_from_rsp(rsp, "molds") == [self.mold_id]
#
#         # fetch all
#         rsp = self.get("/plugins/ccxi/tags")
#         assert_status_ok(rsp)
#
#     def question(self):
#         # add mold
#         data = {"name": "Test (1).pdf", "molds": [self.mold_id], "tags": [self.tag_id]}
#         rsp = self.put(f"/plugins/fileapi/file/{self.file_id}", json_data=data)
#         assert_status_ok(rsp)
#
#         rsp = self.get(f"/plugins/fileapi/tree/{self.tree_id}")
#         assert_status_ok(rsp)
#         file = get_from_rsp(rsp, "files")[0]
#
#         self.question_id = file["questions"][0]["id"]
#
#         # submit answer
#         data = {
#             "schema": {
#                 "schemas": [
#                     {
#                         "name": "test",
#                         "orders": ["全称"],
#                         "schema": {
#                             "全称": {"type": "文本", "required": False, "multi": True, "name": "全称", "_index": 3}
#                         },
#                     }
#                 ],
#                 "schema_types": [],
#                 "version": "5a81a93dcbd51b1b9b93f8b4dfe58dc4",
#                 "mold_type": 0,
#             },
#             "userAnswer": {
#                 "version": "2.2",
#                 "items": [
#                     {
#                         "key": '["test:0","全称:0"]',
#                         "data": [
#                             {
#                                 "boxes": [
#                                     {
#                                         "box": {
#                                             "box_left": 65.38461538461539,
#                                             "box_top": 70,
#                                             "box_right": 100,
#                                             "box_bottom": 92.3076923076923,
#                                         },
#                                         "page": 0,
#                                         "text": "Test",
#                                     }
#                                 ],
#                                 "handleType": "wireframe",
#                             }
#                         ],
#                         "value": "",
#                         "schema": {
#                             "data": {"label": "全称", "type": "文本", "required": False, "multi": True, "words": ""}
#                         },
#                         "manual": True,
#                     }
#                 ],
#             },
#             "custom_field": {"version": "2.2", "items": []},
#         }
#         rsp = self.post(f"/question/{self.question_id}/answer?save_data_only=0", json_data={"data": data})
#         assert_status_ok(rsp)
#
#         # delete mold
#         data = {"name": "Test (1).pdf", "molds": [], "tags": [self.tag_id]}
#         rsp = self.put(f"/plugins/fileapi/file/{self.file_id}", json_data=data)
#         assert_status_ok(rsp)
#
#         rsp = self.get(f"/plugins/fileapi/file/search?fileid={self.file_id}")
#         file = get_from_rsp(rsp, "items")[0]
#         assert not file["molds"]
#         assert not file["questions"]
#
#     def external_file_upload(self):
#         headers = {"access-token": "eyJzdWIiOiIxMjM"}
#         self.external_upload(headers)
#         self.external_upload_for_ht(headers)
#
#     def external_upload(self, headers):
#         data = {
#             "text": "123456",
#             "filename": "text_test",
#         }
#         if get_config("client.name", "") == "csc":
#             url = "/info/idoc/scriber/upload"
#             data.update(
#                 {
#                     "treeId": self.tree_id,
#                     "schemaId": self.mold_id,
#                 }
#             )
#         else:
#             url = "/external_api/v1/upload"
#             data.update({"tree_id": self.tree_id})
#
#         rsp = self.post(url, data=data, headers=headers)
#         filename = get_from_rsp(rsp, "filename")
#         assert filename == "text_test.txt"
#
#     def external_upload_for_ht(self, headers):
#         if get_config("client.name", "") == "csc":
#             return
#         url = "/external_api/v1/scriber_fund/upload"
#         files = {"file": ("test.pdf", localstorage.read_file(TestFilePath), "application/pdf")}
#         data = {
#             "tree_id": self.tree_id,
#             "schema_id": self.mold_id,
#             "username": "admin",
#         }
#         rsp = self.post(url, files=files, data=data, headers=headers)
#         filename = get_from_rsp(rsp, "filename")
#         assert filename == "test.pdf"
#
#     def tearDown(self) -> None:
#         del self.tag_id
#         del self.ccx_file_tag_id
#         del self.question_id
#         super(TestFileApi, self).tearDown()
