import re
from argparse import ArgumentParser
from datetime import datetime
from getpass import getpass

import dateutil.parser

from jira import JIRA


from togglsync.config import Config
from togglsync.helpers.date_time_helper import DateTimeHelper


class JiraTimeEntry:
    """https://docs.atlassian.com/software/jira/docs/api/REST/8.6.0/?_ga=2.176164261.1400572.1578483550-1368931921.1548406408#api/2/issue-getWorklog
    """

    toggl_id_pattern = "\[toggl#([0-9]+)\]"

    def __init__(self, id, created_on, user, seconds, started, issue, comments):
        self.id = id
        self.created_on = created_on
        self.user = user
        self.seconds = seconds
        self.spent_on = started
        self.issue = issue
        self.comments = comments
        self.toggl_id = self.findToggleId(comments)

    def __str__(self):
        return "{0.id} {0.created_on} ({0.user}), {0.seconds}s, @{0.spent_on}, {0.issue}: {0.comments} (toggl_id: {0.toggl_id})".format(
            self
        )

    @classmethod
    def findToggleId(cls, comment):
        if comment == None:
            return None

        found = re.search(cls.toggl_id_pattern, comment)
        return int(found.group(1)) if found else None

    @classmethod
    def fromWorklog(cls, jiraWorklog):
        # https://jira.readthedocs.io/en/latest/examples.html#fields
        return cls(
            jiraWorklog.id,
            dateutil.parser.parse(jiraWorklog.created),  # raw value is ISO string
            jiraWorklog.author.name,
            jiraWorklog.timeSpentSeconds,
            dateutil.parser.parse(jiraWorklog.started),  # raw value is ISO string
            jiraWorklog.issueId,  # issue.id, not issue.key!
            jiraWorklog.comment,
        )


class JiraHelper:
    def __init__(self, url, user, passwd, simulation):
        self.url = url
        self.simulation = simulation

        self.jira_api = JIRA(url, basic_auth=(user, passwd))

        if simulation:
            print("JiraHelper is in simulation mode")

    def get(self, issue_key):
        try:
            for worklog in self.jira_api.worklogs(issue_key):
                yield JiraTimeEntry.fromWorklog(worklog)
        except Exception as exc:
            raise Exception(
                "Error downloading time entries for {}: {}".format(issue_key, str(exc))
            )

    def put(self, issueId, started: datetime, seconds, comment):
        datetime.now()
        if self.simulation:
            print(
                "\t\tSimulate create of: {}, {}, {}, {}".format(
                    issueId, started, seconds, comment
                )
            )
        else:
            self.jira_api.add_worklog(issueId, timeSpentSeconds=seconds, started=started, comment=comment)

    def update(self, id, issueId, started, seconds, comment):
        if self.simulation:
            print(
                "\t\tSimulate update of: {}, {}, {}, {} (#{})".format(
                    issueId, started, seconds, comment, id
                )
            )
        else:
            worklog = self.jira_api.worklog(issueId, id)
            worklog.update(timeSpentSeconds=seconds, started=started, comment=comment)

    def delete(self, id, issueId):
        if self.simulation:
            print("\t\tSimulate delete of: {}".format(id))
        else:
            worklog = self.jira_api.worklog(issueId, id)
            worklog.delete()


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Downloads work logs for given issue (--issue) or adds work log with given time in seconds (--time)"
    )

    parser.add_argument("-i", "--issue", help="Issue id", required=True, type=str)
    parser.add_argument("-t", "--time", help="Seconds spent")
    parser.add_argument("-c", "--comment", help="Comment")
    parser.add_argument("-n", "--num", help="Config entry number", default=0, type=int)

    args = parser.parse_args()

    config = Config.fromFile()
    jira_username = config.entries[args.num].jira_username
    jira_pass = getpass(prompt="Jira password [{}]:".format(jira_username))
    helper = JiraHelper(config.jira, jira_username, jira_pass, simulation=False)

    if args.time:
        print("Saving...")
        helper.put(args.issue, datetime.now(), args.time, args.comment)
    else:
        print("Getting worklogs...")
        result = helper.get(args.issue)
        for r in result:
            print(str(r))

