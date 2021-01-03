import os
import re
from argparse import ArgumentParser
from datetime import datetime
from getpass import getpass

import dateutil.parser
import dateutil.tz
from jira import JIRA
from termcolor import colored

from togglsync.config import Config, Colors


class JiraTimeEntry:
    """https://docs.atlassian.com/software/jira/docs/api/REST/8.6.0/?_ga=2.176164261.1400572.1578483550-1368931921.1548406408#api/2/issue-getWorklog
    """

    toggl_id_pattern = "\[toggl#([0-9]+)\]"

    def __init__(
        self,
        id,
        created_on,
        user,
        seconds,
        started,
        issue,
        comments,
        jira_issue_id=None,
    ):
        self.id = id
        self.created_on = created_on
        self.user = user
        self.seconds = seconds
        if seconds:
            self.hours = self.secondsToHours(seconds)
        self.spent_on = started
        self.issue = issue
        self.comments = comments
        self.toggl_id = self.findToggleId(comments)
        self.jira_issue_id = jira_issue_id

    def __str__(self):
        return "{0.id} {0.created_on} ({0.user}), {0.seconds}s, @{0.spent_on}, {0.issue}: {0.comments} (toggl_id: {0.toggl_id})".format(
            self
        )

    @staticmethod
    def secondsToHours(seconds):
        return round(seconds / 3600.0, 2)

    @staticmethod
    def findUserName(user):
        try:
            return user.name
        except AttributeError:
            return user.emailAddress

    @classmethod
    def findToggleId(cls, comment):
        if comment == None:
            return None

        found = re.search(cls.toggl_id_pattern, comment)
        return int(found.group(1)) if found else None

    @classmethod
    def fromWorklog(cls, jiraWorklog, issue_key):
        # https://jira.readthedocs.io/en/latest/examples.html#fields
        # raw datetime value is ISO string, tz-aware, local timezone
        created_utc = dateutil.parser.parse(jiraWorklog.created).astimezone(
            dateutil.tz.UTC
        )
        started_utc = dateutil.parser.parse(jiraWorklog.started).astimezone(
            dateutil.tz.UTC
        )

        return cls(
            jiraWorklog.id,
            created_utc.isoformat(),
            cls.findUserName(jiraWorklog.author),
            jiraWorklog.timeSpentSeconds,
            started_utc.isoformat(),
            issue_key,  # as worklog.issueId is internal numeric value not issue.key
            jiraWorklog.comment if hasattr(jiraWorklog, "comment") else None,
            jira_issue_id=jiraWorklog.issueId,  # issue.id, not issue.key!
        )


class JiraHelper:
    def __init__(self, url, user, passwd, simulation):
        self.url = url
        self.simulation = simulation
        self.user_name = user

        if url:
            self.jira_api = JIRA(url, basic_auth=(user, passwd))

        if simulation:
            print(colored("Jira is in simulation mode", Colors.IMPORTANT.value))

    @staticmethod
    def round_to_minutes(seconds):
        return round(seconds / 60) * 60

    @classmethod
    def dictFromTogglEntry(cls, togglEntry):
        # by default Jira truncates time to full minutes (cuts seconds portion of the time)
        # which creates big difference over a longer period of time
        rounded_to_minutes = cls.round_to_minutes(togglEntry.seconds)
        return {
            "issueId": togglEntry.taskId,
            "started": togglEntry.start,
            "seconds": rounded_to_minutes,
            "comment": "{} [toggl#{}]".format(togglEntry.description, togglEntry.id),
        }

    def get(self, issue_key):
        try:
            for worklog in self.jira_api.worklogs(issue_key):
                try:
                    if worklog.author.name == self.user_name:
                        yield JiraTimeEntry.fromWorklog(worklog, issue_key)
                except:
                    if worklog.author.emailAddress == self.user_name:
                        yield JiraTimeEntry.fromWorklog(worklog, issue_key)
        except Exception as exc:
            raise Exception(
                "Error downloading time entries for {}: {}".format(issue_key, str(exc))
            )

    def put(self, issueId, started: datetime, seconds, comment):
        if isinstance(started, str):
            started = dateutil.parser.parse(started)
        if int(seconds) < 60:
            print(
                colored(
                    "\t\tCan't add entries under 1 min: {}, {}, {}, {}".format(
                        issueId, str(started), seconds, comment
                    ),
                    Colors.ERROR.value,
                )
            )
            return
        if self.simulation:
            print(
                "\t\tSimulate create of: {}, {}, {}, {}".format(
                    issueId, str(started), seconds, comment
                )
            )
        else:
            # add_worklog "started" is expected as datetime
            self.jira_api.add_worklog(
                issueId, timeSpentSeconds=seconds, started=started, comment=comment
            )

    def update(self, id, issueId, started, seconds, comment):
        # have to get the exact dt format, otherwise will get an Http-500
        if isinstance(started, str):
            started = dateutil.parser.parse(started)
        started = started.strftime("%Y-%m-%dT%H:%M:%S.000%z")
        if int(seconds) < 60:
            print(
                colored(
                    "\t\tCan't update entries to under 1 min, deleting instead: {}, {}, {}, {}".format(
                        issueId, str(started), seconds, comment
                    ),
                    Colors.UPDATE.value,
                )
            )
            self.delete(id, issueId)
            return

        if self.simulation:
            print(
                "\t\tSimulate update of: {}, {}, {}, {} (#{})".format(
                    issueId, started, seconds, comment, id
                )
            )
        else:
            worklog = self.jira_api.worklog(issueId, id)
            # update "started" is expected as str
            print("\t\tUpdate: {}s on {} with {}".format(seconds, started, comment))
            worklog.update(timeSpentSeconds=seconds, started=started, comment=comment)

    def delete(self, id, issueId):
        if self.simulation:
            print("\t\tSimulate delete of: {}".format(id))
        else:
            worklog = self.jira_api.worklog(issueId, id)
            worklog.delete()
            print(colored("\t\tDeleted entry for: {}".format(issueId), Colors.UPDATE.value))


def get_jira_pass():
    if os.environ.get("TOGGL_JIRA_PASS", None):
        return os.environ["TOGGL_JIRA_PASS"]
    else:
        return getpass(prompt="Jira password [{}]:".format(config_entry.jira_username))


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Downloads work logs for given issue (--issue) or adds work log with given time in seconds (--time)"
    )

    default_start_time = datetime.now(dateutil.tz.tzlocal()).isoformat()
    parser.add_argument("-i", "--issue", help="Issue id", required=True, type=str)
    parser.add_argument("-t", "--time", help="Seconds spent")
    parser.add_argument("-c", "--comment", help="Comment")
    parser.add_argument("-u", "--update", help="Worklog id to update")
    parser.add_argument(
        "-s",
        "--started",
        help="Start datetime of worklog",
        default=default_start_time,
        type=str,
    )
    parser.add_argument("-n", "--num", help="Config entry number", default=0, type=int)

    args = parser.parse_args()

    config = Config.fromFile()
    config_entry = config.entries[args.num]
    jira_username = config_entry.jira_username
    jira_pass = get_jira_pass()
    helper = JiraHelper(
        config_entry.jira_url, jira_username, jira_pass, simulation=False
    )

    if args.time and args.update:
        print("Updating {} ...".format(args.update))
        helper.update(
            int(args.update), args.issue, args.started, args.time, args.comment
        )
    elif args.time:
        print("Saving...")
        helper.put(args.issue, args.started, args.time, args.comment)
    else:
        print("Getting worklogs...")
        result = helper.get(args.issue)
        for r in result:
            print(str(r))
