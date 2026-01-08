# CYC: skip-file
import asyncio
import datetime
import functools
import logging
import multiprocessing
import platform
import struct
from multiprocessing import cpu_count, get_context
from multiprocessing.connection import Connection
from multiprocessing.pool import Pool, ThreadPool
from typing import Callable, Iterator

from remarkable.common.util import loop_wrapper
from remarkable.config import get_config

logger = logging.getLogger(__name__)


def _send_bytes(self, buf):
    buf_length = len(buf)
    if buf_length > 2147483647:
        pre_header = struct.pack("!i", -1)
        header = struct.pack("!Q", buf_length)
        self._send(pre_header)
        self._send(header)
        self._send(buf)
    else:
        # For wire compatibility with 3.2 and lower
        header = struct.pack("!i", buf_length)
        if buf_length > 16384:
            # The payload is large so Nagle's algorithm won't be triggered
            # and we'd better avoid the cost of concatenation.
            self._send(header)
            self._send(buf)
        else:
            # Issue #20540: concatenate before sending, to avoid delays due
            # to Nagle's algorithm on a TCP socket.
            # Also note we want to avoid sending a 0-length buffer separately,
            # to avoid "broken pipe" errors if the other end closed the pipe.
            self._send(header + buf)


def _recv_bytes(self, maxsize=None):
    buf = self._recv(4)
    (size,) = struct.unpack("!i", buf.getvalue())
    if size == -1:
        buf = self._recv(8)
        (size,) = struct.unpack("!Q", buf.getvalue())
    if maxsize is not None and size > maxsize:
        return None
    return self._recv(size)


Connection._send_bytes = _send_bytes
Connection._recv_bytes = _recv_bytes


def _error_callback(func, args, error_value):
    logging.error(f'Func: "{func.__name__}", args : "{args}", error: "{error_value}"')


def _get_real_func(func: Callable):
    # asyncio.iscoroutinefunction returns false for Cython async function objects.
    # https://github.com/cython/cython/issues/2273
    return (
        _get_real_func(func.__wrapped__)
        if isinstance(getattr(func, "__wrapped__", None), type(_get_real_func))
        else func
    )


def is_coroutine_func(func: Callable):
    return asyncio.iscoroutinefunction(func) or asyncio.iscoroutinefunction(_get_real_func(func))


def run_in_multiprocess(
    func, tasks, workers=0, debug=False, callback=None, maxtasksperchild=10, pool_type="process", ctx_method="fork"
):
    multiprocessing_option = get_config("app.multiprocessing", "enable")
    if multiprocessing_option == "disable":
        logger.debug(f"multiprocessing is {multiprocessing_option}, {func.__name__}run in single process")
        debug = True

    if platform.system() == "Darwin":
        try:
            multiprocessing.set_start_method("spawn")
            ctx_method = "spawn"
        except RuntimeError:
            pass

    if debug:
        if not is_coroutine_func(func):
            return [run_func(func, task) for task in tasks]
        # NOTE: can't run 2 different ioloop in single process, you will get a
        # RuntimeError: Cannot run the event loop while another loop is running
        return [run_coro_func(func, task) for task in tasks]

    if not tasks:
        return []

    if not workers:
        workers = 4
    workers = min(workers, len(tasks) if isinstance(tasks, list) else 4)

    if pool_type == "process":
        pool = Pool(processes=workers, maxtasksperchild=maxtasksperchild, context=get_context(ctx_method))
    else:
        # TODO: raise "gino.exceptions.InitializedError: Cannot reuse a closed bakery" when more than one threads
        decorated = func.__code__.co_name != func.__name__ and func.__code__.co_name == "run_in_loop"
        pool = ThreadPool(processes=1 if decorated else workers)
    rets = []
    rets_async = []
    for task in tasks:
        _callback = functools.partial(callback, task) if callback else None
        error_callback = functools.partial(_error_callback, func, task)
        if not is_coroutine_func(func):
            ret_async = pool.apply_async(run_func, (func, task), callback=_callback, error_callback=error_callback)
        else:
            ret_async = pool.apply_async(run_coro_func, (func, task), callback=_callback, error_callback=error_callback)
        rets_async.append(ret_async)

    pool.close()
    pool.join()

    if rets_async:
        rets = [r.get() for r in rets_async if r.successful()]

    return rets


@loop_wrapper
async def run_coro_func(func, args):
    try:
        return await run_func(func, args)
    except Exception as e:
        raise Exception(str(e)) from e


def run_func(func, args):
    try:
        if isinstance(args, tuple) and _get_real_func(func).__code__.co_argcount > 1:
            return func(*args)
        # NOTE: 兼容旧方式，func 参数打包成一个 tuple
        return func(args)
    except Exception as e:
        raise Exception(str(e)) from e


def run_by_batch(
    func: callable,
    tasks: tuple | list | Iterator,
    batch_size=0,
    workers=0,
    debug=False,
    callback=None,
    ctx_method="fork",
):
    create_at = datetime.datetime.now()

    if not batch_size:
        batch_size = cpu_count() // 2

    if not isinstance(tasks, Iterator):
        tasks = iter(tasks)

    task_count = 0
    task_group = []
    while True:
        try:
            task_group.append(next(tasks))
        except StopIteration:
            if task_group:
                yield run_in_multiprocess(
                    func, task_group, workers=workers, debug=debug, callback=callback, ctx_method=ctx_method
                )
            break
        if len(task_group) >= batch_size:
            yield run_in_multiprocess(
                func, task_group, workers=workers, debug=debug, callback=callback, ctx_method=ctx_method
            )
            task_count += batch_size
            task_group = []

    task_count += len(task_group)
    total_cost = (datetime.datetime.now() - create_at).total_seconds()
    logger.info(f'Func: "{func.__name__}", task counts: {task_count}, total cost: {total_cost}s.')
