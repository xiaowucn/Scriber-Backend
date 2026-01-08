from remarkable.security.authtoken import _generate_token


class TestAuthTokenTestCase:
    def test_auth_token(self, monkeypatch):
        appid = 'scriber'
        secret = '30a89d6b53627ddc4618f9954a5c4225'
        url = 'http://sda.chinastock.com.cn/scriber/api/v1/plugins/cgs/files/upload'
        _timestamp = '1679036371'
        _token = 'd12fd2a322951ea331bc3dc2578e18e9'

        monkeypatch.setattr("remarkable.security.authtoken.config.get_config", lambda x: False)

        token = _generate_token(url, appid, secret, timestamp=_timestamp, exclude_domain=True)
        assert token == _token

    def test_auth_token_without_subpath(self, monkeypatch):
        appid = 'scriber'
        secret = '30a89d6b53627ddc4618f9954a5c4225'
        url = 'http://sda.chinastock.com.cn/scriber/api/v1/plugins/cgs/files/upload'
        _timestamp = '1679036371'
        _token = 'f5bdc6e94683bfb65b205c92b9d59d18'

        monkeypatch.setattr("remarkable.security.authtoken.config.get_config", lambda x: True)

        token = _generate_token(url, appid, secret, timestamp=_timestamp, exclude_domain=True)
        assert token == _token
