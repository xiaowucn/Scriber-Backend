import json
from io import BytesIO
from unittest import mock
from unittest.mock import patch, AsyncMock

import attr
import pytest
import yaml
from tornado.httpclient import HTTPClientError

from remarkable.checker.cgs_checker.cgs_esb_client import MOCKED_DATA, ESBClient
from remarkable.plugins.cgs.utils import create_cgs_params
from tests.utils import mock_get_config

test_config_patch = """
cgs:
  auth:
    app_id: 'cgs'
    secret_key: '069f0ba4d5c635e9b98fb94b7cd98cc4'
    zero_padding: True
  default:
    mid: 0 #默认模型id，设置0表示无默认配置
    tree_id: 1 #默认文档树id
  audit: True
  esb:
    debug: False  # 银河ESB调用调试模式，生产环境设置成False或者删除
    apis:
      sda:
        url: 'http://10.4.5.161:22112/apiJson/V2/SDA'
        function_no: 'YH0028000400005'  # 功能号
        function_version: '1'  # 功能号版本
        caller_system_code: 'SDA'  # 调方系统代码，由ESB系统告知
      manager:
        url: 'http://10.4.5.161:22112/edp-query-b2b/gbes/V1/general/getChfManagerInfo'
        function_no: 'YH0028000400009'  # 功能号
        function_version: '1'  # 功能号版本
        caller_system_code: 'SDA'  # 调方系统代码，由ESB系统告知
    user: 'sda'  # 用户名，根据对接银河ESB环境需要调整
    password: 'rkTj3v8na2Sg4b'  # 密码，根据对接银河ESB环境需要调整
    call_timeout: 10  # 调用ESB超时时间，单位：秒
"""


@attr.s
class MockedRequest:
    text = attr.ib()
    status_code = attr.ib(default=200)

    def json(self):
        return json.loads(self.text)


class TestCGSApi:
    test_config = yaml.safe_load(BytesIO(test_config_patch.encode("utf8")))
    mock_get_config = mock.MagicMock(side_effect=mock_get_config(test_config))

    @pytest.mark.gen_test
    @patch("remarkable.plugins.cgs.utils.config.get_config", mock_get_config)
    @patch("remarkable.plugins.cgs.auth.config.get_config", mock_get_config)
    async def test_validate_token(self, http_client, monkeypatch):
        user = {
            "uid": "1111111",
            "uname": "显示名称",
            "sys_code": "PIF",  # PIF, OAS, FMP
        }

        url = "/api/v1/plugins/cgs/files/1/schemas/1/audit"
        params = create_cgs_params(url, user)
        relative_url = url.replace("/api/v1", "")
        with pytest.raises(HTTPClientError, match="HTTP 404: Not Found") as error:
            await http_client.fetch(f"{relative_url}?{params}", api_version="v1")

    @pytest.mark.asyncio(loop_scope="class")
    @patch("remarkable.checker.cgs_checker.cgs_esb_client.config.get_config", mock_get_config)
    async def test_sda_api(self, monkeypatch):
        name = "中国银河投资管理有限公司"

        client = ESBClient()
        with monkeypatch.context() as m:
            post_mock = AsyncMock(return_value=MockedRequest(text=json.dumps(MOCKED_DATA[name])))
            m.setattr("remarkable.checker.cgs_checker.cgs_esb_client.httpx.AsyncClient.post", post_mock)

            res = await client.get_sda_info(name)

            assert res[0] == MOCKED_DATA[name]["data"]["Datas"][0]

    @pytest.mark.asyncio(loop_scope="class")
    @patch("remarkable.checker.cgs_checker.cgs_esb_client.config.get_config", mock_get_config)
    async def test_get_chf_manager_info_api(self, monkeypatch):
        name = "中国银河投资管理有限公司"

        client = ESBClient()
        with monkeypatch.context() as m:
            post_mock = AsyncMock(return_value=MockedRequest(text=json.dumps(MOCKED_DATA[name])))
            m.setattr("remarkable.checker.cgs_checker.cgs_esb_client.httpx.AsyncClient.post", post_mock)

            res = await client.get_chf_manager_info(name)

            assert res[0] == MOCKED_DATA[name]["data"]["Datas"][0]
