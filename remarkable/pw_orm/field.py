import json

from cryptography.fernet import Fernet
from peewee import SQL, Cast, CharField, IntegerField, fn
from playhouse.mysql_ext import JSONField as MySQLJSONField  # noqa
from playhouse.postgres_ext import ArrayField as PGArrayField  # noqa
from playhouse.postgres_ext import BinaryJSONField as PGJSONBField  # noqa
from psycopg2.extras import Json

from remarkable import config
from remarkable.db import IS_MYSQL


class _MySQLArrayField(MySQLJSONField):
    def __init__(
        self, field_class=IntegerField, field_kwargs=None, dimensions=1, convert_values=False, *args, **kwargs
    ):
        self.__field = field_class(**(field_kwargs or {}))
        self.dimensions = dimensions
        self.convert_values = convert_values
        self.field_type = self.__field.field_type
        super().__init__(*args, **kwargs)


class _PGArrayField(PGArrayField):
    pass


class _MySQLJSONField(MySQLJSONField):
    def __init__(self, json_type="json", json_dumps=None, json_loads=None, **kwargs):
        self.json_type = json_type
        super().__init__(json_dumps, json_loads, **kwargs)


class _PGJSONBField(PGJSONBField):
    """
    项目中同时有json和jsonb字段, 在使用时统一当成jsonb处理

    需要注意的地方
    1. 插入时需要cast成真实的类型
    """

    def __init__(self, json_type="jsonb", dumps=None, *args, **kwargs):
        self.dumps = dumps or json.dumps
        super().__init__(*args, **kwargs)
        self.json_type = json_type

    def db_value(self, value):
        if value is None:
            return value
        if not isinstance(value, Json):
            return Cast(self.dumps(value), self.json_type)
        return value

    def python_value(self, value):
        if value is None:
            return value
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except TypeError:
            return value


if IS_MYSQL:

    class JSONField(_MySQLJSONField):
        pass

    class ArrayField(_MySQLArrayField):
        def contains(self, value):
            if isinstance(value, list):
                value = fn.JSON_ARRAY(*value)
            else:
                value = fn.JSON_ARRAY(value)
            return fn.JSON_CONTAINS(self, value, "$")

        def contains_any(self, values):
            values = [str(value) for value in values]
            return fn.JSON_CONTAINS(self, SQL(f"""CAST('["{",".join(values)}"]' AS JSON)"""), "$")
else:

    class JSONField(_PGJSONBField):
        pass

    class ArrayField(_PGArrayField):
        pass


class EncryptedCharField(CharField):
    """可逆加密的文本字段"""

    @property
    def cipher_suite(self):
        if key := config.get_config("client.email_password_key"):
            return Fernet(key)
        return None

    def db_value(self, value):
        # 存入数据库时加密
        if value is None:
            return None
        if not self.cipher_suite:
            return value
        if isinstance(value, str):
            value = value.encode("utf-8")
        encrypted = self.cipher_suite.encrypt(value)
        return encrypted.decode("utf-8")

    def python_value(self, value):
        # 从数据库读取时解密
        if value is None:
            return None
        if not self.cipher_suite:
            return value
        decrypted = self.cipher_suite.decrypt(value.encode("utf-8"))
        return decrypted.decode("utf-8")
