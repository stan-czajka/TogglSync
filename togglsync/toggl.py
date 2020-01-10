import requests
import json
import re
from argparse import ArgumentParser

from togglsync.config import Config
from togglsync.helpers.date_time_helper import DateTimeHelper


class TogglEntry:
    """
    Class containing single toggl time entry
    """

    pattern = "#[0-9]{1,}"

    def __init__(self, entry, duration, start, id, description):
        self.entry = entry
        self.duration = duration
        self.start = start
        self.id = id
        self.description = description

        self.taskId = TogglEntry.findTaskId(self.description)
        self.hours = TogglEntry.secondsToHours(self.duration)

    def toDict(self):
        return {
            "issueId": self.taskId,
            "spentOn": self.start[:10],
            "hours": self.hours,
            "comment": "{} [toggl#{}]".format(self.description, self.id),
        }

    @classmethod
    def createFromEntry(cls, entry):
        return cls(
            entry,
            entry["duration"],
            entry["start"],
            entry["id"],
            entry["description"] if "description" in entry else "",
        )

    @staticmethod
    def secondsToHours(seconds):
        return round(seconds / 3600.0, 2)

    @staticmethod
    def findTaskId(desc):
        if not desc:
            return None

        found = re.findall(TogglEntry.pattern, desc)

        if len(found) > 0:
            return int(found[0][1:])

        return None

    def __str__(self):
        return "toggl#{}. {}: {} (time: {} h, task id: {})".format(
            self.id,
            self.start,
            self.description,
            self.hours,
            "#" + str(self.taskId) if self.taskId else "-",
        )

    def __repr__(self):
        return str(self)


class TogglHelper:
    """
    Class providing access to toggl time entries
    API: https://github.com/toggl/toggl_api_docs/blob/master/chapters/time_entries.md
    """

    def __init__(self, url, togglApiKey):
        self.url = url
        self.togglApiKey = togglApiKey

    def get(self, days):
        print("Downloading since: {} day{}".format(days, "s" if days > 1 else ""))

        start = DateTimeHelper.get_date_in_past(days) + "+02:00"
        end = DateTimeHelper.get_today_midnight() + "+02:00"

        print("Statrt:\t{}".format(start))
        print("End:\t{}".format(end))

        auth = (self.togglApiKey, "api_token")
        params = {"start_date": start, "end_date": end}

        r = requests.get(self.url + "time_entries", auth=auth, params=params)

        if r.status_code != 200:
            raise Exception("Not expected status code: {}".format(r.status_code))

        for entry in r.json():
            yield TogglEntry.createFromEntry(entry)

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

    toggl = TogglHelper(config.toggl, config.entries[args.num].toggl)

    for entry in toggl.get(args.days):
        print(str(entry))
