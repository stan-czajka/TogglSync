import unittest
from unittest.mock import Mock, MagicMock

from togglsync.config import Entry
from togglsync.jira_wrapper import JiraTimeEntry, JiraHelper
from togglsync.synchronizer import Synchronizer
from togglsync.toggl import TogglEntry, TogglHelper


class SynchronizerJiraTests(unittest.TestCase):
    jira_config = Entry("test", task_patterns=["SLUG-[0-9]+"])

    def test_start_one_day_empty(self):
        jira = JiraHelper(None, None, None, False)
        toggl = TogglHelper("url", None)
        toggl.get = MagicMock()

        s = Synchronizer(Mock(), jira, toggl, None, raise_errors=True)
        s.start(1)

        toggl.get.assert_called_once_with(1)

    def test_start_one_day_single(self):
        jira = JiraHelper(None, None, None, False)
        toggl = TogglHelper("url", None)
        toggl.get = Mock()

        toggl.get.return_value = [
            TogglEntry(
                None, 3600, "2016-03-02T01:01:01", 777, "test SLUG-333", self.jira_config
            )
        ]

        jira.get = Mock()
        jira.get.return_value = [
            JiraTimeEntry(
                777,
                "2016-01-01T01:02:03",
                "john doe",
                3600,
                "2016-03-02T01:01:01",
                "SLUG-333",
                "test SLUG-333 [toggl#777]",
            )
        ]
        jira.update = MagicMock()

        s = Synchronizer(Mock(), jira, toggl, None, raise_errors=True)
        s.start(1)

        toggl.get.assert_called_once_with(1)
        jira.get.assert_called_once_with('SLUG-333')
        jira.update.assert_not_called()

    def test_groupTogglByIssueId(self):
        entries = [
            TogglEntry(None, 3600, None, 1, "SLUG-15", self.jira_config),
            TogglEntry(None, 3600, None, 2, "SLUG-16", self.jira_config),
            TogglEntry(None, 3600, None, 3, "SLUG-16", self.jira_config),
            TogglEntry(None, 3600, None, 4, "SLUG-16", self.jira_config),
            TogglEntry(None, 3600, None, 5, "SLUG-17", self.jira_config),
        ]

        groups = Synchronizer.groupTogglByIssueId(entries)

        self.assertIsNotNone(groups)

        self.assertEqual(3, len(groups))

        self.assertTrue("SLUG-15" in groups)
        self.assertTrue("SLUG-16" in groups)
        self.assertTrue("SLUG-17" in groups)

        self.assertEquals(1, len(groups["SLUG-15"]))
        self.assertEquals(3, len(groups["SLUG-16"]))
        self.assertEquals(1, len(groups["SLUG-17"]))

        self.assertEquals(1, groups["SLUG-15"][0].id)
        self.assertEquals(2, groups["SLUG-16"][0].id)
        self.assertEquals(3, groups["SLUG-16"][1].id)
        self.assertEquals(4, groups["SLUG-16"][2].id)
        self.assertEquals(5, groups["SLUG-17"][0].id)

    def test_groupRedmineByIssueId(self):
        entries = [
            JiraTimeEntry(66, None, None, None, None, 1, "[toggl#21]"),
            JiraTimeEntry(67, None, None, None, None, 2, "[toggl#22]"),
            JiraTimeEntry(68, None, None, None, None, 2, "[toggl#23]"),
            JiraTimeEntry(69, None, None, None, None, 2, "[toggl#24]"),
        ]

        groups = Synchronizer.groupDestinationByIssueId(entries)

        self.assertEquals(2, len(groups))

        self.assertTrue(1 in groups)
        self.assertTrue(2 in groups)

        self.assertEquals(1, len(groups[1]))
        self.assertEquals(3, len(groups[2]))

        self.assertEquals(22, groups[2][0].toggl_id)
        self.assertEquals(23, groups[2][1].toggl_id)
        self.assertEquals(24, groups[2][2].toggl_id)

    def test_sync_single_toggl_no_jira(self):
        config = MagicMock()
        jira = JiraHelper(None, None, None, False)
        jira.get = Mock()
        jira.put = Mock()
        toggl = TogglHelper("url", None)
        toggl.get = Mock()

        toggl.get.return_value = [
            TogglEntry(
                None,
                3600,
                "2016-01-01T01:01:01",
                17,
                "SLUG-987 hard work",
                self.jira_config,
            )
        ]

        jira.get.return_value = []

        s = Synchronizer(config, jira, toggl, None, raise_errors=True)
        s.start(1)

        toggl.get.assert_called_once_with(1)

        jira.put.assert_called_once_with(
            issueId="SLUG-987",
            started="2016-01-01T01:01:01",
            seconds=3600,
            comment="SLUG-987 hard work [toggl#17]",
        )

    def test_sync_single_toggl_already_inserted_in_jira(self):
        jira = JiraHelper(None, None, None, False)
        jira.get = Mock()
        jira.put = Mock()
        jira.update = Mock()
        toggl = TogglHelper("url", None)
        toggl.get = Mock()

        toggl.get.return_value = [
            TogglEntry(
                None,
                3600,
                "2016-01-01T01:01:01",
                17,
                "SLUG-987 hard work",
                self.jira_config,
            )
        ]

        jira.get.return_value = [
            JiraTimeEntry(
                222,
                "2016-05-01T04:02:22",
                "john doe",
                3600,
                "2016-01-01T01:01:01",
                "SLUG-987",
                "SLUG-987 hard work [toggl#17]",
            )
        ]

        s = Synchronizer(MagicMock(), jira, toggl, None, raise_errors=True)
        s.start(1)
        jira.update.assert_not_called()
        jira.put.assert_not_called()

    def test_sync_single_toggl_modified_entry(self):
        jira = JiraHelper(None, None, None, False)
        jira.get = Mock()
        jira.update = Mock()
        toggl = TogglHelper("url", None)
        toggl.get = Mock()

        toggl.get.return_value = [
            TogglEntry(
                None,
                2 * 3600,
                "2016-01-01T01:01:01",
                17,
                "SLUG-987 hard work",
                self.jira_config,
            )
        ]

        jira.get.return_value = [
            JiraTimeEntry(
                222,
                "2016-05-01T04:02:22",
                "john doe",
                1,
                "2016-01-01T01:01:01",
                "SLUG-987",
                "SLUG-987 hard work [toggl#17]",
            )
        ]

        s = Synchronizer(MagicMock(), jira, toggl, None, raise_errors=True)
        s.start(1)

        jira.update.assert_called_once_with(
            id=222,
            issueId="SLUG-987",
            started="2016-01-01T01:01:01",
            seconds=2 * 3600,
            comment="SLUG-987 hard work [toggl#17]",
        )

    def test_ignore_negative_duration(self):
        """
        Synchronizer should ignore entries with negative durations (pending entries).

		From toggl docs:
           duration: time entry duration in seconds. If the time entry is currently running, the duration attribute contains a negative value, denoting the start
           of the time entry in seconds since epoch (Jan 1 1970). The correct duration can be calculated as current_time + duration, where current_time is the current
           time in seconds since epoch. (integer, required)
        """

        jira = JiraHelper(None, None, None, False)
        jira.get = Mock()
        jira.put = Mock()
        toggl = TogglHelper("url", None)
        toggl.get = Mock()

        toggl.get.return_value = [
            TogglEntry(
                None, 3600, "2016-01-01T01:01:01", 777, "test SLUG-333", self.jira_config
            ),
            TogglEntry(
                None,
                -3600,
                "2016-01-01T01:01:01",
                778,
                "test SLUG-334",
                self.jira_config,
            ),
        ]

        jira.get.return_value = []

        s = Synchronizer(Mock(), jira, toggl, None, raise_errors=True)
        s.start(1)

        toggl.get.assert_called_once_with(1)
        jira.get.assert_called_once_with("SLUG-333")

        jira.put.assert_called_once_with(
            issueId="SLUG-333",
            started="2016-01-01T01:01:01",
            seconds=3600,
            comment="test SLUG-333 [toggl#777]",
        )

    def create_test_entries_pair(self):
        toggl = TogglEntry(
            None, 3600, "2020-01-13T08:11:04+00:00", 777, "test SLUG-333", self.jira_config
        )
        jira = JiraTimeEntry(
            "987654321",
            created_on="2020-01-13T08:11:04.000+00:00",
            user="user",
            seconds=3600,
            started="2020-01-13T08:11:04.000+00:00",
            issue="SLUG-333",
            comments="test SLUG-333 [toggl#777]",
            jira_issue_id="12345",
        )
        return toggl, jira

    def test_equal_exact(self):
        toggl, jira = self.create_test_entries_pair()

        helper = JiraHelper(None, None, None, False)
        sync = Synchronizer(None, helper, None, None)
        self.assertTrue(sync._equal(toggl, jira))

    def test_equal_rounding_to_min(self):
        toggl, jira = self.create_test_entries_pair()
        toggl.seconds += 30

        helper = JiraHelper(None, None, None, False)
        sync = Synchronizer(None, helper, None, None)
        self.assertTrue(sync._equal(toggl, jira))

    def test_equal_diff_time(self):
        toggl, jira = self.create_test_entries_pair()
        toggl.seconds = 120

        helper = JiraHelper(None, None, None, False)
        sync = Synchronizer(None, helper, None, None)
        self.assertFalse(sync._equal(toggl, jira))

    def test_equal_diff_started(self):
        toggl, jira = self.create_test_entries_pair()
        toggl.start = "2016-12-25T01:01:01"

        helper = JiraHelper(None, None, None, False)
        sync = Synchronizer(None, helper, None, None)
        self.assertFalse(sync._equal(toggl, jira))

    def test_equal_diff_comment(self):
        toggl, jira = self.create_test_entries_pair()
        toggl.description = "changed SLUG-333"

        helper = JiraHelper(None, None, None, False)
        sync = Synchronizer(None, helper, None, None)
        self.assertFalse(sync._equal(toggl, jira))


if __name__ == "__main__":
    unittest.main()
