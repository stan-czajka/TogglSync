import unittest
from datetime import datetime, date

from togglsync.jira_wrapper import JiraTimeEntry


class UserStub:
    def __init__(self, name):
        self.name = name
        self.key = name
        self.displayName = name


class JiraWorklogStub:
    def __init__(self, id, created_on, user, seconds, started, issueId, comment):
        self.id = id
        self.author = UserStub(user)
        self.updateAuthor = UserStub(user)
        self.comment = comment
        self.created = datetime.isoformat(created_on)
        self.updated = datetime.isoformat(created_on)
        self.started = datetime.isoformat(started)
        self.timeSpent = "{}s".format(seconds)
        self.timeSpentSeconds = seconds
        self.id = id
        self.issueId = issueId


class JiraTimeEntryTests(unittest.TestCase):
    def testCreatefromWorklog(self):
        stub = JiraWorklogStub(
            1234,
            datetime(2016, 1, 1, 11, 20, 0),
            "john",
            120,
            datetime(2016, 3, 1, 10, 38, 0),
            234123,
            "no comment",
        )
        entry = JiraTimeEntry.fromWorklog(stub)

        self.assertEquals(datetime(2016, 1, 1, 11, 20, 0), entry.created_on)
        self.assertEquals("john", entry.user)
        self.assertEquals(120, entry.seconds)
        self.assertEquals(datetime(2016, 3, 1, 10, 38, 0), entry.spent_on)
        self.assertEquals(stub.issueId, entry.issue)
        self.assertEquals(stub.comment, entry.comments)
        self.assertIsNone(entry.toggl_id)

    def testCreatefromWorklog_with_toggle_id(self):
        stub = JiraWorklogStub(
            1234,
            datetime(2016, 1, 1, 11, 20, 0),
            "john",
            120,
            datetime(2016, 3, 1, 10, 38, 0),
            234123,
            "no comment [toggl#987654321]",
        )
        entry = JiraTimeEntry.fromWorklog(stub)

        self.assertEquals(entry.toggl_id, 987654321)

    def testStr(self):
        entry = JiraTimeEntry(
            17, datetime(2016, 1, 1, 11, 20, 0), "john doe", 3, datetime(2016, 3, 1, 11, 20, 0), "GWP-1234", "no comment"
        )
        self.assertEquals(
            str(entry),
            "17 2016-01-01 11:20:00 (john doe), 3s, @2016-03-01 11:20:00, GWP-1234: no comment (toggl_id: None)",
        )

    def testFindTogglId(self):
        self.assertEquals(
            1234, JiraTimeEntry.findToggleId("Work on some things [toggl#1234]")
        )

    def testFindTogglId_no_id(self):
        self.assertEquals(None, JiraTimeEntry.findToggleId("Work on some things"))

    def testFindTogglId_none(self):
        self.assertEquals(None, JiraTimeEntry.findToggleId(None))


if __name__ == "__main__":
    unittest.main()
