"""Synchronization service functions."""

from remarkable.db import init_rdb


def clear_sync_schedule_lock() -> None:
    """Clear the synchronization schedule lock in Redis.

    This function removes the schedule lock key used by the answer poster
    to prevent concurrent synchronization tasks.
    """
    from remarkable.plugins.answer_poster.tasks import ScheduleTaskMonitor

    rdb = init_rdb()
    rdb.delete(ScheduleTaskMonitor.schedule_lock_key)
