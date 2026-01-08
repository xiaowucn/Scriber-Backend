import datetime
import gettext
import inspect
import os
import types
from pathlib import Path

import pytest
import pytest_asyncio
import tornado
import tornado.gen
import tornado.httpclient
import tornado.httpserver
import tornado.testing

from remarkable.config import get_config
from remarkable.db import GinoDB
from remarkable.server import Application
from tests.client import AsyncClient
from tests.utils import mock_session

iscoroutinefunction = inspect.iscoroutinefunction

def _get_async_test_timeout():
    try:
        return float(os.environ.get('ASYNC_TEST_TIMEOUT'))
    except (ValueError, TypeError):
        return 20 * 10


def pytest_configure(config):
    config.addinivalue_line("markers",
                            "gen_test(timeout=None): "
                            "mark the test as asynchronous, it will be "
                            "run using tornado's event loop")


def _argnames(func):
    if hasattr(inspect, "signature"):
        sig = inspect.signature(func)
        return [name for name, param in sig.parameters.items()
                if param.default is param.empty]
    else:
        spec = inspect.getargspec(func)
        if spec.defaults:
            return spec.args[:-len(spec.defaults)]
        if isinstance(func, types.FunctionType):
            return spec.args
        # Func is a bound method, skip "self"
        return spec.args[1:]


def _timeout(item):
    default_timeout = _get_async_test_timeout()
    gen_test = item.get_closest_marker('gen_test')
    if gen_test:
        return gen_test.kwargs.get('timeout', default_timeout)
    return default_timeout


@pytest.mark.tryfirst
def pytest_pycollect_makeitem(collector, name, obj):
    if collector.funcnamefilter(name) and inspect.isgeneratorfunction(obj):
        item = pytest.Function.from_parent(collector, name=name)
        if 'gen_test' in item.keywords:
            return list(collector._genfunctions(name, obj))


def pytest_runtest_setup(item):
    if 'gen_test' in item.keywords and 'io_loop' not in item.fixturenames:
        # inject an event loop fixture for all async tests
        item.fixturenames.append('io_loop')


@pytest.mark.tryfirst
def pytest_pyfunc_call(pyfuncitem):
    gen_test_mark = pyfuncitem.get_closest_marker('gen_test')
    if gen_test_mark:
        io_loop = pyfuncitem.funcargs.get('io_loop')
        run_sync = gen_test_mark.kwargs.get('run_sync', True)

        funcargs = dict((arg, pyfuncitem.funcargs[arg])
                        for arg in _argnames(pyfuncitem.obj))
        if iscoroutinefunction(pyfuncitem.obj):
            coroutine = pyfuncitem.obj
            future = tornado.gen.convert_yielded(coroutine(**funcargs))
        else:
            coroutine = tornado.gen.coroutine(pyfuncitem.obj)
            future = coroutine(**funcargs)
        if run_sync:
            io_loop.run_sync(lambda: future, timeout=_timeout(pyfuncitem))
        else:
            # Run this test function as a coroutine, until the timeout. When completed, stop the IOLoop
            # and reraise any exceptions

            future_with_timeout = tornado.gen.with_timeout(
                    datetime.timedelta(seconds=_timeout(pyfuncitem)),
                    future)
            io_loop.add_future(future_with_timeout, lambda f: io_loop.stop())
            io_loop.start()

            # This will reraise any exceptions that occurred.
            future_with_timeout.result()

        # prevent other pyfunc calls from executing
        return True


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def io_loop():
    """Create an instance of the `tornado.ioloop.IOLoop` for each test case.
    """
    io_loop = tornado.ioloop.IOLoop.current()

    yield io_loop

    io_loop.close(all_fds=True)


@pytest.fixture(scope="session")
def pdf_file_bytes(project_root) -> bytes:
    with open(f"{project_root}/data/tests/TestFile.pdf", 'rb') as f:
        return f.read()


def create_test_app(locales_dir, language="zh_CN"):
    app = Application()
    _language_type = get_config("client", {}).get("language", "zh_CN")
    gettext.translation("Scriber-Backend", locales_dir, languages=[_language_type], fallback=True).install()

    return app


def create_server(root_dir):
    server_port = tornado.testing.bind_unused_port()
    locales_dir = os.path.join(root_dir, "i18n", "locales")

    app = create_test_app(locales_dir)
    server = tornado.httpserver.HTTPServer(app)
    server.add_socket(server_port[0])

    return server


@pytest.fixture(scope="session")
def http_server(request, io_loop):
    root_dir = request.getfixturevalue('project_root')
    server = create_server(root_dir)

    yield server

    server.stop()
    if hasattr(server, 'close_all_connections'):
        io_loop.run_sync(server.close_all_connections,
                         timeout=_get_async_test_timeout())


@pytest_asyncio.fixture(loop_scope="module", scope="module")
def module_http_server(request):
    root_dir = request.getfixturevalue('project_root')
    io_loop = tornado.ioloop.IOLoop(make_current=False)

    server = create_server(root_dir)

    yield server

    server.stop()
    if hasattr(server, 'close_all_connections'):
        io_loop.run_sync(server.close_all_connections,
                         timeout=_get_async_test_timeout())

    io_loop.close(all_fds=True)


@pytest.fixture
def login(request):
    m = request.getfixturevalue('monkeypatch')
    def _login(handler, user=None):
        if user is None:
            user = {"uid": "1"}
        m.setattr(handler, "_on_initialized", lambda x: mock_session(x, user))

    return _login


@pytest.fixture(scope="session")
def http_client(http_server) -> AsyncClient:
    client = AsyncClient(force_instance=True, http_server=http_server)

    yield client

    client.close()


@pytest.fixture(scope="module")
def module_http_client(module_http_server) -> AsyncClient:
    client = AsyncClient(force_instance=True, http_server=module_http_server)

    yield client

    client.close()


@pytest.fixture(scope="function")
def create_gino_db():
    def _inner():
        return GinoDB()

    return _inner
