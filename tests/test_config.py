import os
from unittest import TestCase, mock

from remarkable.config import Config

config_data = {
    "_new_entry": {"feature.use_fastapi": "web.use_fastapi"},
    "app": {
        "app_id": "hello",
    },
    "web": {"data_dir": "{project_root}/data/files/", "plugins": ["fileapi", "debug", "sse"]},
    "db": {
        "host": "localhost",
        "port": 12345,
        "dbname": "fake_name",
        "user": "fake_user",
    },
    "debug": True,
    "logging": {"level": "info"},
    "complex_config": "hello",
    "wow": "{logging.level}",
}

user_config_data = {
    "app": {
        "app_id": "hello_user",
    },
    "db": {
        "port": 54321,
        "dbname": "real name",
        "password": "xxxx",
    },
    "debug": False,
    "logging": {"level": "debug"},
    "redis": {"host": "127.0.0.1", "port": 6379},
    "complex_config": {"outer": {"inner": {"a": "1", "b": "2"}}, "outer_1": "outer 1"},
}

test_config_data = {
    "db": {
        "dbname": "db_test",
    },
}


def patched_load_config(env):
    if "config-usr" in env:
        return user_config_data
    elif "config-test" in env:
        return test_config_data
    else:
        return config_data


class TestConfig(TestCase):
    def setUp(self) -> None:
        self.cls_vars_patcher = mock.patch.dict(Config.pre_defined_vars, {"project_root": "/project_root"}, clear=True)
        self.load_config_patcher = mock.patch.object(Config, "_load_config", patched_load_config)
        patched_env = {
            "SCRIBER_CONFIG_APP_APP_ID": "hello_world",
            "SCRIBER_CONFIG_DB_PORT": "12345",
            "SCRIBER_CONFIG_LOGGING_LEVEL": "info",
            "SCRIBER_CONFIG_APP_AUTH_PDFINSIGHT_APP_ID": "hello_pdf",
            "SCRIBER_CONFIG_db_host": "1.1.1.1",
            "SCRIBER_CONFIG_HELLO_APPS": "{app.app_id},{app.auth.pdfinsight.app_id}",
            "SCRIBER_CONFIG_db_server_settings_application_name": "Scriber(openGaussDB)",
            "SCRIBER_CONFIG_web_use_fastapi": "true",
        }
        self.env_patcher = mock.patch.dict(os.environ, patched_env, clear=True)

        self.cls_vars_patcher.start()
        self.load_config_patcher.start()
        self.env_patcher.start()

    def tearDown(self) -> None:
        self.cls_vars_patcher.stop()
        self.load_config_patcher.stop()
        self.env_patcher.stop()

    def test_config_init_from_file(self):
        with mock.patch("os.path.isfile", return_value=False):
            config = Config.from_file("dev")
            config.reload()

            assert config.config_data == config_data

            assert config.get("db.port") == 12345
            assert config.get("web.plugins") == ["fileapi", "debug", "sse"]
            assert config.get("web.data_dir") == "/project_root/data/files/"
            assert config.get("debug") is False
            assert config.get("logging") == {"level": "info"}
            assert config.get("wow") == "info"
            assert config.get("non_exist_key", default="uu") == "uu"
            assert config.get("non_exist_key") is None
            assert config.get("non_exist_key.ff", default="xx") == "xx"
            assert config.get("non_exist_key.ff") is None

    def test_config_merging_custom_user_config_and_replace_with_os_environ_vars(self):
        with mock.patch("os.path.isfile", return_value=True):
            config = Config.from_file("dev")
            config.reload()
            assert config.config_data == {
                "_new_entry": {"feature.use_fastapi": "web.use_fastapi"},
                "app": {
                    "app_id": "hello_user",
                },
                "web": {"data_dir": "{project_root}/data/files/", "plugins": ["fileapi", "debug", "sse"]},
                "db": {
                    "host": "localhost",
                    "port": 54321,
                    "dbname": "db_test",
                    "user": "fake_user",
                    "password": "xxxx",
                },
                "debug": False,
                "logging": {"level": "debug"},
                "wow": "{logging.level}",
                "redis": {"host": "127.0.0.1", "port": 6379},
                "complex_config": {"outer": {"inner": {"a": "1", "b": "2"}}, "outer_1": "outer 1"},
            }

            assert config.get("db.host") == "1.1.1.1"
            assert config.get("web.plugins") == ["fileapi", "debug", "sse"]
            assert config.get("web.data_dir") == "/project_root/data/files/"
            assert config.get("debug") is False
            assert config.get("logging") == {"level": "info"}
            assert config.get("complex_config.outer") == {"inner": {"a": "1", "b": "2"}}
            assert config.get("complex_config.outer_1") == "outer 1"
            assert config.get("app.app_id") == "hello_world"
            assert config.get("app.auth.pdfinsight.app_id") == "hello_pdf"
            assert config.get("hello.apps") == "hello_world,hello_pdf"
            assert config.get("hello")["apps"] == "hello_world,hello_pdf"
            assert config.get("db.server_settings") == {
                "application": {"name": "Scriber(openGaussDB)"},
                "application_name": "Scriber(openGaussDB)",
            }
            # 旧的环境变量仍然可以使用
            assert config.get("feature.use_fastapi") is True
