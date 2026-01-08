import http
import json
from unittest import mock
from unittest.mock import patch

import pytest
from tornado.httpclient import HTTPClientError
from utensils.util import generate_timestamp

from remarkable.security.authtoken import encode_test_url, encode_test_url_v2
from remarkable.user import handlers
from tests.utils import mock_session, mock_get_config


@pytest.mark.gen_test
async def test_should_return_401(http_client):
    with pytest.raises(HTTPClientError, match="HTTP 401: Unauthorized") as error:
        await http_client.fetch("/user/me", api_version="v1")


@pytest.mark.gen_test
async def test_should_get_user_info_and_logout(http_client, monkeypatch):
    url = "/user/me"

    with monkeypatch.context() as m:
        m.setattr(handlers.UserMeHandler, "initialize", lambda handler: mock_session(handler, {"uid": "1"}))

        response = await http_client.fetch(url, api_version="v1")
        assert response.code == 200
        data = json.loads(response.body)["data"]
        assert data["id"] == 1
        assert data["name"] == "admin"

        response =  await http_client.fetch("/logout", api_version="v1")
        assert response.code == 200


test_config = {
    "app": {
        "jwt_secret_key": "hello_kitty",
        "simple_token": "eyJzdWIiOiIxMjM"
    }
}
mocked_get_config = mock.MagicMock(side_effect=mock_get_config(test_config))

@pytest.mark.gen_test
@patch("remarkable.security.authtoken.config.get_config", mocked_get_config)
@patch("remarkable.security.crypto_util.get_config", mocked_get_config)
async def test_token_auth(http_client):
    from remarkable.security.crypto_util import encode_jwt
    from remarkable.security.crypto_util import make_bearer_header

    url = f"/test"
    full_url = http_client.get_url(url, "v1")

    # no token
    rsp = await http_client.get(url)
    assert rsp.status_code == http.HTTPStatus.UNAUTHORIZED


    # token with domain
    encoded_url = encode_test_url(full_url, exclude_domain=True)
    rsp = await http_client.get(encoded_url)
    assert rsp.status_code == http.HTTPStatus.OK

    # token without domain
    encoded_url = encode_test_url(full_url, exclude_domain=False)
    rsp = await http_client.get(encoded_url)
    assert rsp.status_code == http.HTTPStatus.OK

    # token auth v2
    encoded_url = encode_test_url_v2(full_url)
    rsp = await http_client.get(encoded_url)
    assert rsp.status_code == http.HTTPStatus.OK

    # simple token
    rsp = await http_client.get(url, headers={"access-token": test_config["app"]["simple_token"]})
    assert rsp.status_code == http.HTTPStatus.OK

    # JWT
    rsp = await http_client.get(url, headers=make_bearer_header(encode_jwt({"sub": "admin"})))
    assert rsp.status_code == http.HTTPStatus.OK

    # JWT with exp
    rsp = await http_client.get(
        url,
        headers=make_bearer_header(encode_jwt({"sub": "admin", "exp": "123"})),
    )
    assert rsp.status_code == http.HTTPStatus.UNAUTHORIZED

    rsp = await http_client.get(
        url,
        headers=make_bearer_header(encode_jwt({"sub": "admin", "exp": f"{generate_timestamp() + 3000}"})),
    )
    assert rsp.status_code == http.HTTPStatus.OK
