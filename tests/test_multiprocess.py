from remarkable.common.multiprocess import run_by_batch


def simple_echo(num):
    return num


async def async_echo(num):
    return num


async def async_wrapped_echo(num):
    return num


def test_run_by_batch():
    for func in simple_echo, async_echo, async_wrapped_echo:
        for idx, ret in enumerate(run_by_batch(func, range(10), batch_size=6)):
            if idx == 0:
                assert ret == [0, 1, 2, 3, 4, 5]
            if idx == 1:
                assert ret == [6, 7, 8, 9]

