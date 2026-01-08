"""
审核模块
"""

from remarkable.checker.cgs_checker import Inspector as CgsInspector
from remarkable.checker.default_checker import Inspector as DefaultInspector
from remarkable.checker.gffunds_checker import Inspector as GffundsInspector
from remarkable.checker.jsfund_checker import Inspector as JsfundInspector
from remarkable.checker.zts_checker import Inspector as ZtsInspector
from remarkable.common.util import import_class_by_path


def load_inspector_config(pkg_path: str):
    if not pkg_path.startswith("remarkable."):
        pkg_path = f"remarkable.checker.{pkg_path}"
    return pkg_path


def make_inspector_instance(inspector_package, file, mold, question):
    clazz = import_class_by_path(f"{inspector_package}.Inspector")
    if clazz:
        return clazz(file, mold, question)
    return None
