from datetime import datetime, timedelta, timezone
from typing import Annotated
from pydantic import PlainSerializer

WIB = timezone(timedelta(hours=7))


def now_wib() -> datetime:
    """
    Mengembalikan waktu saat ini dalam WIB (UTC+7) sebagai naive datetime.
    Disimpan sebagai naive agar PostgreSQL (yang default TimeZone=UTC)
    tidak mengonversi ulang nilainya ke jam UTC saat INSERT ke TIMESTAMP WITHOUT TIME ZONE.
    """
    return datetime.now(WIB).replace(tzinfo=None)


def to_wib_naive(dt: datetime) -> datetime:
    """Mengonversi datetime aware ke WIB naive untuk penyimpanan database."""
    if dt.tzinfo is not None:
        return dt.astimezone(WIB).replace(tzinfo=None)
    return dt


def to_wib(dt: datetime) -> datetime:
    """Memastikan objek datetime bertipe aware dengan zona waktu WIB (+07:00) untuk output JSON/CSV."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=WIB)
    return dt.astimezone(WIB)


WIBDateTime = Annotated[
    datetime,
    PlainSerializer(lambda dt: to_wib(dt).isoformat(), return_type=str)
]
