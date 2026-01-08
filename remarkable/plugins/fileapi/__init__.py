from remarkable.plugins import Plugin

plugin = Plugin(__name__)
external_plugin = Plugin(__name__ + "/external")


def init():
    from . import handlers
