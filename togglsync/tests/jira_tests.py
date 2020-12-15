import unittest
from datetime import datetime, date
import dateutil.tz

from togglsync.config import Entry
from togglsync.jira_wrapper import JiraTimeEntry, JiraHelper
from togglsync.toggl import TogglEntry


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
            datetime(2016, 1, 1, 11, 20, 0, tzinfo=dateutil.tz.UTC),
            "john",
            120,
            datetime(2016, 3, 1, 10, 38, 0, tzinfo=dateutil.tz.UTC),
            234123,
            "no comment",
        )
        entry = JiraTimeEntry.fromWorklog(stub, "PROJ-1234")

        self.assertTrue(False)
        self.assertEquals("2016-01-01T11:20:00+00:00", entry.created_on)
        self.assertEquals("john", entry.user)
        self.assertEquals(120, entry.seconds)
        self.assertEquals("2016-03-01T10:38:00+00:00", entry.spent_on)
        self.assertEquals("PROJ-1234", entry.issue)
        self.assertEquals(stub.issueId, entry.jira_issue_id)
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
        entry = JiraTimeEntry.fromWorklog(stub, "PROJ-1234")

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


class JiraHelperTests(unittest.TestCase):
    jira_config = Entry("test", task_patterns=["SLUG-[0-9]+"])

    def testDictFromTogglEntry(self):
        input = TogglEntry(
            None, 120, "2016-03-02T01:01:01", 777, "test SLUG-333", self.jira_config
        )
        result = JiraHelper.dictFromTogglEntry(input)
        self.assertEquals("SLUG-333", result["issueId"])
        self.assertEquals("2016-03-02T01:01:01", result["started"])
        self.assertEquals(120, result["seconds"])
        self.assertEquals("test SLUG-333 [toggl#777]", result["comment"])

    def testDictFromTogglEntry_time_is_rounded(self):
        input = TogglEntry(
            None, 151, "2016-03-02T01:01:01", 777, "test SLUG-333", self.jira_config
        )
        result = JiraHelper.dictFromTogglEntry(input)
        self.assertEquals(180, result["seconds"])

    def test_round_to_minutes(self):
        self.assertEquals(0, JiraHelper.round_to_minutes(0))
        self.assertEquals(0, JiraHelper.round_to_minutes(29))
        self.assertEquals(0, JiraHelper.round_to_minutes(30))
        self.assertEquals(60, JiraHelper.round_to_minutes(31))
        self.assertEquals(60, JiraHelper.round_to_minutes(59))
        self.assertEquals(60, JiraHelper.round_to_minutes(60))
        self.assertEquals(60, JiraHelper.round_to_minutes(89))
        self.assertEquals(120, JiraHelper.round_to_minutes(90))  # seems strange, but that how default python rounding works
        self.assertEquals(120, JiraHelper.round_to_minutes(91))
        self.assertEquals(120, JiraHelper.round_to_minutes(120))


if __name__ == "__main__":
    unittest.main()
