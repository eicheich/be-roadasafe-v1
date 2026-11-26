from datetime import datetime, timedelta, timezone
from typing import Annotated
from pydantic import PlainSerializer

WIB = timezone(timedelta(hours=7))


def now_wib() -> datetime:
    """Mengembalikan waktu saat ini dalam zona waktu WIB (UTC+7)."""
    return datetime.now(WIB)


def to_wib(dt: datetime) -> datetime:
    """Memastikan objek datetime bertipe aware dengan zona waktu WIB (UTC+7)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=WIB)
    return dt.astimezone(WIB)


WIBDateTime = Annotated[
    datetime,
    PlainSerializer(lambda dt: to_wib(dt).isoformat(), return_type=str)
]
