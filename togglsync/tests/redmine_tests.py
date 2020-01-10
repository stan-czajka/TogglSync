import unittest
from datetime import datetime, date

from togglsync.redmine import RedmineTimeEntry


class UserStub:
    def __init__(self, name):
        self.name = name


class IssueStub:
    def __init__(self, id):
        self.id = id


class RedmineTimeEntryStub:
    def __init__(self, id, created_on, user, hours, spent_on, issue, comments):
        self.id = id
        self.created_on = created_on
        self.user = UserStub(user)
        self.hours = hours
        self.spent_on = spent_on
        self.issue = IssueStub(issue)
        self.comments = comments


class RedmineTimeEntryTests(unittest.TestCase):
    def testCreateFromTimeEntry(self):
        stub = RedmineTimeEntryStub(
            17,
            datetime(2016, 1, 1, 11, 20, 0),
            "john doe",
            3,
            date(2016, 3, 1),
            21,
            "no comment",
        )
        entry = RedmineTimeEntry.fromTimeEntry(stub)

        self.assertEquals(datetime(2016, 1, 1, 11, 20, 0), entry.created_on)
        self.assertEquals(stub.user.name, entry.user)
        self.assertEquals(stub.hours, entry.hours)
        self.assertEquals("2016-03-01", entry.spent_on)
        self.assertEquals(stub.issue.id, entry.issue)
        self.assertEquals(stub.comments, entry.comments)

    def testCreateFromTimeEntry_with_toggle_id(self):
        stub = RedmineTimeEntryStub(
            17,
            datetime(2016, 1, 1, 11, 20, 0),
            "john doe",
            3,
            date(2016, 3, 1),
            21,
            "no comment [toggl#987654321]",
        )
        entry = RedmineTimeEntry.fromTimeEntry(stub)

        self.assertEquals(entry.toggl_id, 987654321)

    def testStr(self):
        entry = RedmineTimeEntry(
            17, "2016-01-01 11:20", "john doe", 3, "2016-03-01", 21, "no comment"
        )
        self.assertEquals(
            str(entry),
            "17 2016-01-01 11:20 (john doe), 3h, @2016-03-01, #21: no comment (toggl_id: None)",
        )

    def testFindTogglId(self):
        self.assertEquals(
            1234, RedmineTimeEntry.findToggleId("Work on some things [toggl#1234]")
        )

    def testFindTogglId_no_id(self):
        self.assertEquals(None, RedmineTimeEntry.findToggleId("Work on some things"))

    def testFindTogglId_none(self):
        self.assertEquals(None, RedmineTimeEntry.findToggleId(None))


if __name__ == "__main__":
    unittest.main()
