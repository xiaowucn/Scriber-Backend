from pkgutil import extend_path, walk_packages

__path__ = extend_path(__path__, __name__)


for importer, modname, _ in walk_packages(__path__, __name__ + "."):
    importer.find_spec(modname).loader.load_module(modname)


from remarkable.hooks.base import InsightFinishHook, InsightStartHook, PredictFinishHook  # noqa: E402

__all__ = ("InsightFinishHook", "PredictFinishHook", "InsightStartHook")
