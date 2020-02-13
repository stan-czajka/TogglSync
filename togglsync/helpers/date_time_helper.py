from datetime import datetime, timedelta

import dateutil.tz


class DateTimeHelper:
    @staticmethod
    def get_date_in_past(days):
        today = datetime.now(dateutil.tz.tzlocal()).replace(hour=0, minute=0, second=0, microsecond=0)
        delta = timedelta(days)
        past = today - delta

        return past.isoformat()

    @staticmethod
    def get_today_midnight():
        today = datetime.now(dateutil.tz.tzlocal()).replace(hour=23, minute=59, second=59, microsecond=0)
        return today.isoformat()

    @staticmethod
    def get_today():
        return datetime.strftime(datetime.today(), "%Y-%m-%d")

    @staticmethod
    def formatDate(d):
        return datetime.strftime(d, "%Y-%m-%d")
