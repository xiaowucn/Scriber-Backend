# pylint: skip-file
import copy
import gettext
import os
import signal
import sys

import tornado
import tornado.httpserver
import tornado.web
from gunicorn.workers.base import Worker
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.options import options

from remarkable.common.util import clear_caches
from remarkable.config import MAX_BUFFER_SIZE


class TornadoWorker(Worker):
    def handle_exit(self, sig, frame):
        if self.alive:
            super(TornadoWorker, self).handle_exit(sig, frame)

    def handle_request(self):
        self.nr += 1
        if self.alive and self.nr >= self.max_requests:
            self.log.info("Autorestarting worker after current request.")
            self.alive = False

    def watchdog(self):
        if self.alive:
            self.notify()

        if self.ppid != os.getppid():
            self.log.info("Parent changed, shutting down: %s", self)
            self.alive = False

    def heartbeat(self):
        if not self.alive:
            if self.server_alive:
                if hasattr(self, "server"):
                    try:
                        self.server.stop()
                    except Exception:
                        pass
                self.server_alive = False
            else:
                for callback in self.callbacks:
                    callback.stop()
                self.ioloop.stop()

    def init_process(self):
        # IOLoop cannot survive a fork or be shared across processes
        # in any way. When multiple processes are being used, each process
        # should create its own IOLoop. We should clear current IOLoop
        # if exists before os.fork.
        IOLoop.clear_current()
        clear_caches()
        super(TornadoWorker, self).init_process()

    def init_signals(self):
        # reset signaling
        for s in self.SIGNALS:
            signal.signal(s, signal.SIG_DFL)
        # init new signaling
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_exit)
        signal.signal(signal.SIGINT, self.handle_quit)
        signal.signal(signal.SIGWINCH, self.handle_winch)
        signal.signal(signal.SIGUSR1, self.handle_usr1)
        signal.signal(signal.SIGABRT, self.handle_abort)

        # Treat SIGHUP as SIGQUIT
        signal.signal(signal.SIGHUP, self.handle_quit)

        # Don't let SIGTERM and SIGUSR1 disturb active requests
        # by interrupting system calls
        signal.siginterrupt(signal.SIGTERM, False)
        signal.siginterrupt(signal.SIGUSR1, False)

        if hasattr(signal, "set_wakeup_fd"):
            signal.set_wakeup_fd(self.PIPE[1])

    def run(self):
        from remarkable.config import get_config, project_root
        from remarkable.db import db

        self.ioloop = IOLoop.current()
        self.alive = True
        self.server_alive = False

        self.callbacks = []
        self.callbacks.append(PeriodicCallback(self.watchdog, 1000))
        self.callbacks.append(PeriodicCallback(self.heartbeat, 1000))
        for callback in self.callbacks:
            callback.start()

        # Assume the app is a WSGI callable if its not an
        # instance of tornado.web.Application or is an
        # instance of tornado.wsgi.WSGIApplication
        app = self.wsgi
        self.ioloop.run_sync(lambda: db.init_app(app, loop=self.ioloop))
        # Monkey-patching HTTPConnection.finish to count the
        # number of requests being handled by Tornado. This
        # will help gunicorn shutdown the worker if max_requests
        # is exceeded.
        httpserver = sys.modules["tornado.httpserver"]
        if hasattr(httpserver, "HTTPConnection"):
            old_connection_finish = httpserver.HTTPConnection.finish

            def finish(other):
                self.handle_request()
                old_connection_finish(other)

            httpserver.HTTPConnection.finish = finish
            sys.modules["tornado.httpserver"] = httpserver

            server_class = tornado.httpserver.HTTPServer
        else:

            class _HTTPServer(tornado.httpserver.HTTPServer):
                def on_close(instance, server_conn):
                    self.handle_request()
                    super(_HTTPServer, instance).on_close(server_conn)

            server_class = _HTTPServer

        app_params = {
            "max_buffer_size": MAX_BUFFER_SIZE,
            "decompress_request": True,
        }
        if self.cfg.is_ssl:
            _ssl_opt = copy.deepcopy(self.cfg.ssl_options)
            # tornado refuses initialization if ssl_options contains following
            # options
            del _ssl_opt["do_handshake_on_connect"]
            del _ssl_opt["suppress_ragged_eofs"]
            app_params["ssl_options"] = _ssl_opt
        server = server_class(app, **app_params)

        # set up translation config
        _locales_dir = os.path.join(project_root, "i18n", "locales")
        _language_type = (get_config("client") or {}).get("language", "zh_CN")
        gettext.translation("Scriber-Backend", _locales_dir, languages=[_language_type], fallback=True).install()

        self.server = server
        self.server_alive = True

        for socket in self.sockets:
            socket.setblocking(0)
            server.add_socket(socket)

        server.no_keep_alive = self.cfg.keepalive <= 0
        server.start(num_processes=1)

        options["logging"] = get_config("logging.level", default="debug")
        self.ioloop.start()
