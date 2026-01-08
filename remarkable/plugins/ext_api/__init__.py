from remarkable import config
from remarkable.base_handler import route
from remarkable.plugins import Plugin


class ExtPlugin(Plugin):
    prefix = "/external_api/v1"
    if (config.get_config("client.name") or "") == "csc":
        prefix = "/info/idoc/scriber"

    def route(self, router_url, prefix=prefix, use_common_prefix=False):
        """重载路由前缀"""
        return route(router_url, prefix=prefix)


def init():
    from . import handlers


plugin = ExtPlugin(__name__)
