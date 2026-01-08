import http
from unittest import mock

import pytest

from remarkable import base_handler
from tests.utils import mock_get_config

test_config_patch = """app:
  # TODO: `single_sign_limit` test
  single_sign_limit: False
"""

time_limit_on_config = {
    "time_limit": {
        "enable": True,
        "offset": 28800,  # 偏移量, 单位秒, 默认为8小时
        "expire_at": "1970-01-01 00:00:00",  # 过期时间
        "path": "/tmp/patch_00.tar.gz",
    }
}

time_limit_not_expired_config = {
    "time_limit": {
        "expire_at": "2199-01-01 00:00:00"
    }
}

time_limit_off_config = {
    "time_limit": {
        "enable": False,
        "expire_at": "1970-01-01 00:00:00" # 过期时间
    }
}

@pytest.mark.gen_test
async def test_user_crud(http_client, login, monkeypatch):
    login(base_handler.BaseHandler)

    new_user = {"name": "test", "password": "test123456"}
    # create
    rsp = await http_client.post(url="/user", json_data=new_user)
    # password too simple
    assert rsp.status_code == 400
    new_user["password"] = "test.123456"
    # normal create
    rsp = await http_client.post(url="/user", json_data=new_user)
    assert rsp.status_code == 200, rsp.text
    uid = rsp.json()["data"]["id"]

    # update
    rsp = await http_client.put(url=f"/user/{uid}", json_data={"name": "hello_kitty"})
    assert rsp.status_code == 200, rsp.text

    # retrieve
    rsp = await http_client.get(url=f"/user/{uid}")
    assert rsp.status_code == 200, rsp.text
    assert rsp.json()["data"]["name"] == "hello_kitty", rsp.text

    # fetch all
    rsp = await http_client.get(url="/user")
    assert rsp.status_code == 200, rsp.text
    assert rsp.json()["data"]["total"] == 2, rsp.text

    # delete
    rsp = await http_client.delete(url=f"/user/{uid}")
    assert rsp.status_code == 200, rsp.text

    rsp = await http_client.get(url=f"user/{uid}")
    assert rsp.status_code == 200 and rsp.json()["status"] == "error", rsp.text

@pytest.mark.gen_test
async def test_time_limit(http_client, monkeypatch, login):
    login(base_handler.BaseHandler)

    with monkeypatch.context() as m:
        mocked = mock.MagicMock(side_effect=mock_get_config(time_limit_on_config))
        m.setattr("remarkable.service.time_limit.get_config", mocked)

        rsp = await http_client.get(url="/user/me")
        assert rsp.status_code == http.HTTPStatus.PAYMENT_REQUIRED, rsp.text

    with monkeypatch.context() as m:
        mocked = mock.MagicMock(side_effect=mock_get_config(time_limit_not_expired_config))
        m.setattr("remarkable.service.time_limit.get_config", mocked)

        rsp = await http_client.get(url="/user/me")
        assert rsp.status_code == http.HTTPStatus.OK, rsp.text

    with monkeypatch.context() as m:
        mocked = mock.MagicMock(side_effect=mock_get_config(time_limit_off_config))
        m.setattr("remarkable.service.time_limit.get_config", mocked)

        rsp = await http_client.get(url="/user/me")
        assert rsp.status_code == http.HTTPStatus.OK, rsp.text