"""Time-zone helpers. Все билеты и периоды активируются в 00:00 по Москве."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

MSK_TZ = ZoneInfo("Europe/Moscow")


def now_msk() -> datetime:
    """Текущее datetime в TZ Москва."""
    return datetime.now(MSK_TZ)


def today_msk() -> date:
    """Текущая дата в TZ Москва. Используется для фильтрации билетов и периодов
    «активен сегодня». Контейнер крутится в UTC, поэтому date.today() даст не то.
    """
    return now_msk().date()
