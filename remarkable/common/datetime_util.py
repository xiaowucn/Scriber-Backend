import datetime
from itertools import groupby


def get_start_end_of_day(dt: datetime.datetime):
    start_at = datetime.datetime.combine(dt, datetime.time(0, 0, 0, 0, dt.tzinfo))
    end_at = start_at + datetime.timedelta(days=1)
    return start_at, end_at


def gen_month_ranges_data(start_at, end_at):
    months = []
    current_month = datetime.datetime.fromtimestamp(start_at).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_moth = datetime.datetime.fromtimestamp(end_at)
    while current_month <= end_moth:
        # 计算该月的开始和结束时间
        start_of_month = current_month

        # 增加到下个月
        if current_month.month == 12:
            current_month = current_month.replace(year=current_month.year + 1, month=1)
            end_of_month = current_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            current_month = current_month.replace(month=current_month.month + 1)
            end_of_month = current_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_of_month.month == end_moth.month and start_of_month.year == end_moth.year:
            # 如果当前月和最后一个月份相同，则使用end_moth
            end_of_month = end_moth.replace(hour=0, minute=0, second=0, microsecond=0)
        # 转换为时间戳
        start_timestamp = int(start_of_month.timestamp())
        end_timestamp = int(end_of_month.timestamp())
        months.append((start_timestamp, end_timestamp))

    return months


def gen_day_ranges(start_at, end_at):
    days = []
    current_day = datetime.datetime.fromtimestamp(start_at)
    while current_day <= datetime.datetime.fromtimestamp(end_at):
        start_of_day, end_of_day = get_start_end_of_day(current_day)
        # 转换为时间戳
        days.append((int(start_of_day.timestamp()), int(end_of_day.timestamp())))
        current_day += datetime.timedelta(days=1)
    return days


def _sort_by_date(obj, attr_name: str = "created_utc"):
    value = getattr(obj, attr_name)
    dt = datetime.datetime.fromtimestamp(value)

    return get_start_end_of_day(dt)[0]


def group_by_date(items, attr_name: str = "created_utc"):
    sorted_items = sorted(items, key=lambda x: _sort_by_date(x, attr_name))
    return groupby(sorted_items, lambda x: _sort_by_date(x, attr_name))


TIME_STAMP_MAX = 4070908800  # 2099年1月1日
