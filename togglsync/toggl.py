import datetime
import re
from argparse import ArgumentParser

import dateutil.parser
import dateutil.tz
import requests

from togglsync.config import Config, Entry
from togglsync.helpers.date_time_helper import DateTimeHelper


class TogglEntry:
    """
    Class containing single toggl time entry
    """

    def __init__(self, raw_entry: dict, duration, start, id, description, config_entry: Entry):
        self.raw_entry = raw_entry
        self.duration = duration
        self.start = start
        self.id = id
        self.description = description
        self.config_entry = config_entry

        self.taskId = self.findTaskId()
        self.hours = TogglEntry.secondsToHours(self.duration)
        self.seconds = self.duration

    @classmethod
    def createFromEntry(cls, entry, config_entry):
        start_utc = dateutil.parser.parse(entry["start"]).astimezone(dateutil.tz.UTC)
        return cls(
            entry,
            entry["duration"],
            start_utc.isoformat(),
            entry["id"],
            entry["description"] if "description" in entry else "",
            config_entry,
        )

    @staticmethod
    def secondsToHours(seconds):
        return round(seconds / 3600.0, 2)

    def findTaskId(self):
        if not self.description or not self.config_entry:
            return None

        for pattern in self.config_entry.task_patterns:
            found = re.findall(pattern, self.description)
            if len(found) > 0:
                match = found[0]
                if isinstance(match, tuple) and len(match) > 1:
                    # if match has groups then return the second group
                    return match[1]
                return match

        return None

    def __str__(self):
        ts = datetime.timedelta(seconds=self.seconds)
        local_time = dateutil.parser.parse(self.start).astimezone(dateutil.tz.tzlocal())
        return "{}: {}, spent: {}, issue: {} [toggl#{}]".format(
            local_time.strftime("%Y-%m-%d %H:%M"),
            self.description,
            str(ts),
            str(self.taskId) if self.taskId else "-",
            self.id,
        )

    def __repr__(self):
        return "toggl#{}. {}: {} (time: {} h, task id: {})".format(
            self.id,
            self.start,
            self.description,
            self.hours,
            str(self.taskId) if self.taskId else "-",
        )


class TogglHelper:
    """
    Class providing access to toggl time entries
    API: https://github.com/toggl/toggl_api_docs/blob/master/chapters/time_entries.md
    """

    def __init__(self, url, config_entry: Entry):
        self.url = url
        self.config_entry = config_entry
        if self.config_entry:
            self.togglApiKey = config_entry.toggl

    def get(self, days):
        print("Downloading since: {} day{}".format(days, "s" if days > 1 else ""))

        start = DateTimeHelper.get_date_in_past(days) + "+02:00"
        end = DateTimeHelper.get_today_midnight() + "+02:00"

        print("Start:\t{}".format(start))
        print("End:\t{}".format(end))

        auth = (self.togglApiKey, "api_token")
        params = {"start_date": start, "end_date": end}

        r = requests.get(self.url + "time_entries", auth=auth, params=params)

        if r.status_code != 200:
            raise Exception("Not expected status code: {}".format(r.status_code))

        for entry in r.json():
            yield TogglEntry.createFromEntry(entry, self.config_entry)

    @staticmethod
    def filterRedmineEntries(entries):
        """
        Filters toggl entries

            - only with redmine id
            - only with positive duration
        """

        return [e for e in entries if e.taskId is not None and e.duration > 0]


if __name__ == "__main__":

    parser = ArgumentParser(description="Gets toggl entries for last n days")

    parser.add_argument("-d", "--days", help="Days", default=1, type=int)
    parser.add_argument("-n", "--num", help="Config entry number", default=0, type=int)

    args = parser.parse_args()

    config = Config.fromFile()

    if args.num >= len(config.entries):
        raise Exception("Invalid num: {}".format(args.num))

    toggl = TogglHelper(config.toggl, config.entries[args.num])

    for entry in toggl.get(args.days):
        print(str(entry))
