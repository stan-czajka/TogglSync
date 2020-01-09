import unittest

from togglsync.toggl import TogglEntry


class TogglEntryTests(unittest.TestCase):
    def test_parse(self):
        entry = TogglEntry.createFromEntry(
            {
                "id": 2121,
                "duration": 255,
                "start": "2016-01-01T09:09:09+02:00",
                "description": "entry description",
            }
        )

        self.assertEquals(2121, entry.id)

    def test_find_task_id_contains(self):
        self.assertEquals(21558, TogglEntry.findTaskId("Long task description #21558"))
        self.assertEquals(21497, TogglEntry.findTaskId("Short #21497"))
        self.assertEquals(24361, TogglEntry.findTaskId("#24361"))
        self.assertEquals(
            24361, TogglEntry.findTaskId("#24361 Task description, with others things")
        )

    def test_find_task_id_empty(self):
        self.assertEquals(None, TogglEntry.findTaskId(""))
        self.assertEquals(None, TogglEntry.findTaskId(None))

    def test_find_task_id_not_contains(self):
        self.assertEquals(None, TogglEntry.findTaskId("Lorem ipsum dolor imet"))

    def test_find_task_id_multiple(self):
        self.assertEquals(
            24361,
            TogglEntry.findTaskId("#24361 Task description, with others things #333"),
        )


if __name__ == "__main__":
    unittest.main()
