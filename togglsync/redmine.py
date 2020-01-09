import json
import re
from argparse import ArgumentParser
from redmine import Redmine
from datetime import datetime

from togglsync.config import Config
from togglsync.helpers.date_time_helper import DateTimeHelper


class RedmineTimeEntry:
    """
		https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries
	"""

    toggl_id_pattern = "\[toggl#([0-9]+)\]"

    def __init__(self, id, created_on, user, hours, spent_on, issue, comments):
        self.id = id
        self.created_on = created_on
        self.user = user
        self.hours = hours
        self.spent_on = spent_on
        self.issue = issue
        self.comments = comments
        self.toggl_id = RedmineTimeEntry.findToggleId(comments)

    def __str__(self):
        return "{0.id} {0.created_on} ({0.user}), {0.hours}h, @{0.spent_on}, #{0.issue}: {0.comments} (toggle_id: {0.toggl_id})".format(
            self
        )

    @staticmethod
    def findToggleId(comment):
        if comment == None:
            return None

        found = re.search(RedmineTimeEntry.toggl_id_pattern, comment)
        return int(found.group(1)) if found else None

    @classmethod
    def fromTimeEntry(cls, redmineTimeEntry):
        return cls(
            redmineTimeEntry.id,
            redmineTimeEntry.created_on,  # datetime
            redmineTimeEntry.user.name,
            redmineTimeEntry.hours,
            DateTimeHelper.formatDate(redmineTimeEntry.spent_on),  # date
            redmineTimeEntry.issue.id,
            redmineTimeEntry.comments
            if hasattr(redmineTimeEntry, "comments")
            else None,
        )


class RedmineHelper:
    def __init__(self, url, entry, simulation):
        self.url = url
        self.entry = entry
        self.simulation = simulation

        self.redmine = Redmine(url, key=entry)

        if simulation:
            print("RedmineHelper is in simulation mode")

    def get(self, id):
        try:
            for t in self.redmine.time_entry.filter(issue_id=id):
                yield RedmineTimeEntry.fromTimeEntry(t)
        except Exception as exc:
            raise Exception(
                "Error downloading time entries for {}: {}".format(id, str(exc))
            )

    def put(self, issueId, spentOn, hours, comment):
        if self.simulation:
            print(
                "\t\tSimulate create of: {}, {}, {}, {}".format(
                    issueId, spentOn, hours, comment
                )
            )
        else:
            self.redmine.time_entry.create(
                issue_id=issueId, spent_on=spentOn, hours=hours, comments=comment
            )

    def update(self, id, issueId, spentOn, hours, comment):
        if self.simulation:
            print(
                "\t\tSimulate update of: {}, {}, {}, {} (#{})".format(
                    issueId, spentOn, hours, comment, id
                )
            )
        else:
            self.redmine.time_entry.update(
                id, issue_id=issueId, spent_on=spentOn, hours=hours, comments=comment
            )

    def delete(self, id):
        if self.simulation:
            print("\t\tSimulate delete of: {}".format(id))
        else:
            self.redmine.time_entry.delete(id)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Downloads and uploads redmine time entries (if no hours provided, then downloads)"
    )

    parser.add_argument("-i", "--issue", help="Issue id", required=True, type=int)
    parser.add_argument("-t", "--time", help="Hours")
    parser.add_argument("-c", "--comment", help="Comment")
    parser.add_argument("-n", "--num", help="Config entry number", default=0, type=int)

    args = parser.parse_args()

    config = Config.fromFile()
    redmine = RedmineHelper(config.redmine, config.entries[args.num].redmine)

    if args.time:
        print("Saving...")
        redmine.put(args.issue, DateTimeHelper.get_today(), args.time, args.comment)
    else:
        result = redmine.get(args.issue)

        for r in result:
            print(str(r))
