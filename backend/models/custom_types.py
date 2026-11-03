from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator
from utils.datetime_utils import to_utc

class UTCDateTime(TypeDecorator):
    """DATETIME column that always stores UTC and always returns an aware UTC datetime.

    SQLite has no timezone support: a plain DateTime silently DROPS the tzinfo, so an aware
    value in UTC-3 would be stored as if it were UTC (3 hours off). This type converts first.
    The DB column stays a plain DATETIME (same schema, same stored text as before).
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        # Python -> DB: convert to UTC, then store without tzinfo (naive UTC)
        if value is None:
            return None
        return to_utc(value).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        # DB -> Python: what is stored is UTC, so mark it as such
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)
