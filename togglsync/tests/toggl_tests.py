import unittest
from unittest import mock

import dateutil.parser
import dateutil.tz

from togglsync.config import Entry
from togglsync.toggl import TogglEntry


class TogglEntryTests(unittest.TestCase):
    sample_config = Entry("test", task_patterns=["SLUG-[0-9]+"])

    def test_parse(self):
        toggl_payload = {
            "id": 2121,
            "duration": 255,
            "start": "2016-01-01T09:09:09+02:00",
            "description": "entry description",
        }
        entry = TogglEntry.createFromEntry(toggl_payload, None)
        self.assertEquals(2121, entry.id)
        self.assertEquals("2016-01-01T07:09:09+00:00", entry.start)

    def test_repr(self):
        entry = TogglEntry(
            None,
            8100,
            "2016-01-01T09:09:09+02:00",
            999,
            "comment SLUG-123",
            self.sample_config,
        )
        self.assertEquals(
            "toggl#999. 2016-01-01T09:09:09+02:00: comment SLUG-123 (time: 2.25 h, task id: SLUG-123)",
            repr(entry),
        )

    def test_str(self):
        entry = TogglEntry(
            None,
            8145,
            "2016-01-01T10:09:09-00:00",
            999,
            "comment SLUG-123",
            self.sample_config,
        )
        with mock.patch("dateutil.tz.tzlocal", return_value=dateutil.tz.gettz("EST")):
            self.assertEquals(
                "2016-01-01 05:09: comment SLUG-123, spent: 2:15:45, issue: SLUG-123 [toggl#999]",
                str(entry),
            )

    @staticmethod
    def find_task_id(patterns, description):
        config_entry = Entry("dummy", None, None, None, None, patterns)
        return TogglEntry(None, 0, None, None, description, config_entry).findTaskId()

    redmine_pattern = "(#)([0-9]{1,})"
    jira_pattern_no_groups = "SLUG-[0-9]+"
    jira_pattern_with_prefix = "(prefix#)(SLUG-[0-9]+)"

    def test_find_task_id_contains_redmine_format(self):
        self.assertEquals(
            "21558",
            self.find_task_id([self.redmine_pattern], "Long task description #21558"),
        )
        self.assertEquals(
            "21497", self.find_task_id([self.redmine_pattern], "Short #21497")
        )
        self.assertEquals("24361", self.find_task_id([self.redmine_pattern], "#24361"))
        self.assertEquals(
            "24361",
            self.find_task_id(
                [self.redmine_pattern], "#24361 Task description, with others things"
            ),
        )

    def test_find_task_id_contains_simple_pattern_format(self):
        self.assertEquals(
            "SLUG-123",
            self.find_task_id([self.jira_pattern_no_groups], "Description SLUG-123"),
        )
        self.assertEquals(
            "SLUG-123",
            self.find_task_id([self.jira_pattern_no_groups], "SLUG-123 Description"),
        )
        self.assertEquals(
            "SLUG-123",
            self.find_task_id(
                [self.jira_pattern_no_groups], "Description SLUG-123 bla"
            ),
        )

    def test_find_task_id_contains_group_pattern_format(self):
        self.assertEquals(
            "SLUG-123",
            self.find_task_id(
                [self.jira_pattern_with_prefix], "Description prefix#SLUG-123"
            ),
        )
        self.assertEquals(
            "SLUG-123",
            self.find_task_id(
                [self.jira_pattern_with_prefix], "prefix#SLUG-123 Description"
            ),
        )
        self.assertEquals(
            "SLUG-123",
            self.find_task_id(
                [self.jira_pattern_with_prefix], "Description prefix#SLUG-123 bla"
            ),
        )

    def test_find_task_id_multiple_patterns(self):
        self.assertEquals(
            "SLUG-123",
            self.find_task_id(
                [self.jira_pattern_no_groups, self.redmine_pattern],
                "Description SLUG-123",
            ),
        )
        self.assertEquals(
            "1234",
            self.find_task_id(
                [self.jira_pattern_no_groups, self.redmine_pattern], "Description #1234"
            ),
        )
        self.assertEquals(
            "SLUG-123",
            self.find_task_id(
                [self.jira_pattern_no_groups, self.redmine_pattern],
                "Description SLUG-123 #1234",
            ),
        )
        self.assertEquals(
            "SLUG-123",
            self.find_task_id(
                [self.jira_pattern_no_groups, self.redmine_pattern],
                "Description #1234 SLUG-123",
            ),
        )
        self.assertEquals(
            "1234",
            self.find_task_id(
                [self.redmine_pattern, self.jira_pattern_no_groups],
                "Description #1234 SLUG-123",
            ),
        )

    def test_find_task_id_empty(self):
        self.assertEquals(None, self.find_task_id([self.redmine_pattern], ""))
        self.assertEquals(None, self.find_task_id([self.redmine_pattern], None))

    def test_find_task_id_not_contains(self):
        self.assertEquals(
            None, self.find_task_id([self.redmine_pattern], "Lorem ipsum dolor imet")
        )

    def test_find_task_id_multiple(self):
        self.assertEquals(
            "24361",
            self.find_task_id(
                [self.redmine_pattern],
                "#24361 Task description, with others things #333",
            ),
        )


if __name__ == "__main__":
    unittest.main()
