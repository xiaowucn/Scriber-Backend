import _pickle as pickle
import base64
import logging
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

import yaml
from peewee import logger as peewee_logger


def _self_path():
    if "__file__" in globals():
        return __file__
    import remarkable

    return remarkable.__file__.replace("__init__", "config")


project_root = os.path.dirname(os.path.dirname(os.path.abspath(_self_path())))

ENV = os.environ.get("ENV") or "dev"
_DEFAULT_CONFIG_PATH = f"{project_root}/config/config-{ENV}.yml"
_BASE_CONFIG_PATH = f"{project_root}/config/config-base.yml"
_USER_CONFIG_PATH = f"{project_root}/config/config-usr.yml"
_TEST_CONFIG_PATH = f"{project_root}/config/config-test.yml"
IS_TEST_ENV = os.path.exists(_TEST_CONFIG_PATH)
MAX_BUFFER_SIZE = 300 * 1024 * 1024  # 300M
_PREDEFINED_VARS = {
    "project_root": project_root,
}
logger = logging.getLogger(__name__)
P_PG_SCHEMA = re.compile(r"-c\s+search_path=(\w+)", re.ASCII)


def target_path(*args):
    return os.path.join(project_root, *args)


def dump_confusion(data, path=None):
    from remarkable.security.crypto_util import aes_encrypt

    data = base64.encodebytes(aes_encrypt(pickle.dumps(data), key="6e154a01080751bdf56f182e6847e852"))
    if not path:
        return data
    with open(path, "wb") as cfile:
        cfile.write(data)


def load_confusion(data=None, path=None):
    from remarkable.security.crypto_util import aes_decrypt

    if path:
        with open(path, "rb") as cfile:
            data = cfile.read()
    return pickle.loads(aes_decrypt(base64.decodebytes(data), key="6e154a01080751bdf56f182e6847e852"))


def _merge(default, usr):
    if isinstance(default, dict) and isinstance(usr, dict):
        for key, value in usr.items():
            if key not in default or any(not isinstance(i, dict) for i in (default[key], value)):
                default[key] = value
            else:
                _merge(default[key], value)
    return default


def fill_vars(value, predefined_vars=None):
    if predefined_vars is None:
        predefined_vars = _PREDEFINED_VARS
    if isinstance(value, dict):
        return {key: fill_vars(value, predefined_vars) for key, value in value.items()}
    if isinstance(value, (str, bytes)):
        for var in re.finditer(r"\{([^}]+)\}", value):
            if var.group(1) in predefined_vars:
                value = value.format(**predefined_vars)
            else:
                expected_value = get_config(var.group(1))
                if expected_value is None:
                    return var.group(0)
                value = value.replace(var.group(0), str(expected_value))
    return value


def get_config(key_string="", default=None):
    # if default is not None:
    #     warnings.warn(
    #         f'"{key_string}": We will remove the "default" parameter in the future, please set the default value in BASE config file.',
    #         DeprecationWarning,
    #         stacklevel=2,
    #     )
    if key_string == "training_cache_dir":
        return _config.training_cache_dir
    if key_string == "db.schema":
        return _get_non_public_schema()
    return _config.get(key_string, default)


@lru_cache(maxsize=1)
def _get_non_public_schema() -> str:
    if options := get_config("db.options"):
        if match := P_PG_SCHEMA.search(options):
            return match.group(1).lower()
    return "public"


def yml2ctc():
    dump_confusion(Config.load_config(_BASE_CONFIG_PATH), f"{os.path.splitext(_BASE_CONFIG_PATH)[0]}.ctc")
    dump_confusion(_config.config_data, f"{os.path.splitext(_config.config_path)[0]}.ctc")


def init_setup():
    log_level = get_config("logging.level") or "info"  # only info/debug is allowed
    logging.basicConfig(
        level=logging.INFO if log_level.lower() == "info" else logging.DEBUG,
        format="%(asctime)s - [%(levelname)s] [%(threadName)s] (%(module)s:%(lineno)d) %(message)s",
    )
    # Turn off the annoying gino SQL echo message
    # https://github.com/python-gino/gino/issues/710#issuecomment-663363092
    for name in (
        "gino.engine._SAEngine",
        "pikepdf",
        "httpx",
        "calliper",
    ):
        logging.getLogger(name).setLevel(logging.ERROR)
    if get_config("logging.queries"):
        peewee_logger.addHandler(logging.StreamHandler())
        peewee_logger.setLevel(logging.DEBUG)


def replace_value_by_environ(ret, env_key, envs):
    if not isinstance(ret, dict):
        if env_value := envs.get(env_key):
            if isinstance(env_value, str):
                ret = yaml.load(envs[env_key], Loader=yaml.SafeLoader) if "{" not in envs[env_key] else envs[env_key]
            elif isinstance(env_value, dict):
                ret = env_value
        return ret
    for key, value in ret.items():
        sub_env_name = "{}_{}".format(env_key, key.lower())
        ret[key] = replace_value_by_environ(value, sub_env_name, envs)
    return ret


class Config:
    env_prefix = "SCRIBER_CONFIG_"
    new_entry_key = "_new_entry"  # 存放新旧配置项映射关系的key
    pre_defined_vars = _PREDEFINED_VARS

    def __init__(self, config_path):
        self._cache = {}
        self._training_cache_dir: Path | None = None
        self.config_path = config_path
        self.config_data = self.load_config(config_path)

    @classmethod
    def from_file(cls, path: str | None = None) -> "Config":
        if path is None:
            path = (
                _DEFAULT_CONFIG_PATH
                if os.path.isfile(_DEFAULT_CONFIG_PATH)
                else f"{os.path.splitext(_DEFAULT_CONFIG_PATH)[0]}.ctc"
            )
        config = cls(path)
        config.validate()
        return config

    def validate(self):
        if self.get("feature.role_based_permission") and self.get("web.user_system_provider") == "trident":
            raise RuntimeError("Role-based permission is not supported for trident user system provider.")

    @property
    def envs(self):
        real_envs = {
            k.lower().replace(self.env_prefix.lower(), "", 1): v
            for k, v in os.environ.items()
            if k.upper().startswith(self.env_prefix)
        }
        new_envs = {}
        for key, value in sorted(real_envs.items(), key=lambda x: x[0].count("_")):
            if "TIME_LIMIT_" in key:
                continue
            self._recursive_build_dict(key.split("_"), value, new_envs)
        return new_envs

    @classmethod
    def _recursive_build_dict(cls, keys, value, cur_dict):
        if not isinstance(cur_dict, dict):  # Check if cur_dict is a leaf node
            return
        for idx in range(len(keys)):
            key_segment = "_".join(keys[: idx + 1]).lower()
            if key_segment not in cur_dict:
                cur_dict[key_segment] = {} if idx != len(keys) - 1 else value
            if idx != len(keys) - 1:
                cls._recursive_build_dict(keys[idx + 1 :], value, cur_dict[key_segment])
            else:
                cur_dict[key_segment] = value

    def reload(self):
        self._cache = {}
        self.config_data = self.load_config(self.config_path)

    def get(self, key_string, default=None):
        has_key = True
        env_key = key_string.replace(".", "_").lower()
        if key_string not in self._cache or env_key in self.envs:
            ret = self.config_data
            keys = [key.strip() for key in key_string.split(".") if key]
            for key in keys:
                ret = ret.get(key)
                if ret is None:
                    ret = default
                    has_key = False
                    break
            ret = replace_value_by_environ(ret, env_key, self.envs)
            if not has_key:
                if previous_key := self.config_data.get(self.new_entry_key, {}).get(key_string):
                    logger.warning(
                        f'Config key "{previous_key}" will be deprecated, please use "{key_string}" instead.'
                    )
                    return self.get(previous_key, default)
                return fill_vars(ret, self.pre_defined_vars)
            self._cache[key_string] = fill_vars(ret, self.pre_defined_vars)
        return self._cache[key_string]

    @classmethod
    def load_config(cls, path: str):
        # config 优先级：测试配置 > 用户配置 > 环境变量 > 基础配置
        config_data = cls._load_config(path)
        if os.path.splitext(path)[0] == os.path.splitext(_BASE_CONFIG_PATH)[0]:
            return config_data

        # if os.path.isfile(_BASE_CONFIG_PATH):
        #     config_data = _merge(cls._load_config(_BASE_CONFIG_PATH), config_data)

        # merge with 'feature' from config-base.yml
        if config := cls._load_config(_BASE_CONFIG_PATH):
            if feature := config.get("feature"):
                config_data = _merge({"feature": feature}, config_data)
            if speedy := config.get("speedy"):
                config_data = _merge({"speedy": speedy}, config_data)

        # merge with user custom config
        if os.environ.get("CI", False):
            custom_paths = (_TEST_CONFIG_PATH,)
        else:
            custom_paths = (_USER_CONFIG_PATH, _TEST_CONFIG_PATH)
        for path in custom_paths:
            if config := cls._load_config(path):
                config_data = _merge(config_data, config)

        return config_data

    def merge(self, other):
        _merge(self.config_data, other)

    @classmethod
    def _load_config(cls, filepath):
        part = os.path.splitext(filepath)[0]
        path = part + ".ctc"
        if os.path.exists(path):
            return load_confusion(path=path)

        path = part + ".yml"
        if os.path.exists(path):
            with open(path, encoding="utf-8") as file_obj:
                return yaml.safe_load(file_obj)

    @property
    def training_cache_dir(self) -> str:
        if not self._training_cache_dir:
            training_cache_dir = f"training_cache{'_test' if IS_TEST_ENV else ''}"
            if _config.get("dev.unique_training_cache_dir"):
                training_cache_dir += f"_{_config.get('db.dbname')}"
            cache_dir = Path(project_root) / "data" / training_cache_dir
            if not cache_dir.exists():
                os.makedirs(cache_dir, exist_ok=True)
            self._training_cache_dir = cache_dir
        return self._training_cache_dir.as_posix()


def pdfparser_env_check():
    """Make sure the environment is set up correctly"""
    env_ver = os.environ.get("LD_PRELOAD")
    assert env_ver is not None, "LD_PRELOAD is not set"
    lib_suffix = ".so" if sys.platform == "linux" else ".dylib"
    assert env_ver.find(f"palladium/libpdfium{lib_suffix}") != -1, (
        f'No "palladium/libpdfium{lib_suffix}" in "LD_PRELOAD"'
    )


# pdfparser_env_check()
_config = Config.from_file()
init_setup()


# only use in tests
def create_test_config():
    return Config.from_file()


if __name__ == "__main__":
    yml2ctc()
