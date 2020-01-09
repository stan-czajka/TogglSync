import unittest

from togglsync.config import Config
from togglsync.config import Entry


class EntryTests(unittest.TestCase):
    def str_test_redmine(self):
        e = Entry("", "<redmine>", "<toggl>")
        self.assertEquals("<toggl>: <redmine>", str(e))

    def str_test_jira(self):
        e = Entry("", None, "<toggl>", "<jira_user>")
        self.assertEquals("<toggl>: <jira_user>", str(e))


class ConfigTests(unittest.TestCase):
    def test_fromFile_config1(self):
        config = Config.fromFile("togglsync/tests/resources/config1.yml")

        self.assertEquals("https://www.toggl.com/api/v8/", config.toggl)
        self.assertEquals("http://redmine.url/", config.redmine)
        self.assertEquals("http://mattermost.url/", config.mattermost["url"])

        self.assertEquals(2, len(config.entries))

        self.assertEquals("entry 1", config.entries[0].label)
        self.assertEquals("redmine-api-key", config.entries[0].redmine)
        self.assertEquals("toggl-api-key", config.entries[0].toggl)

        self.assertEquals("entry 2", config.entries[1].label)
        self.assertEquals("redmine-api-key2", config.entries[1].redmine)
        self.assertEquals("toggl-api-key2", config.entries[1].toggl)

    def test_fromFile_config2(self):
        config = Config.fromFile("togglsync/tests/resources/config2.yml")

        self.assertEquals("https://www.toggl.com/api/v8/", config.toggl)
        self.assertEquals("http://redmine.url/", config.redmine)
        self.assertEquals("http://mattermost.url/", config.mattermost["url"])
        self.assertEquals("#channell", config.mattermost["channel"])

        self.assertEquals(2, len(config.entries))

        self.assertEquals("entry 1", config.entries[0].label)
        self.assertEquals("redmine-api-key", config.entries[0].redmine)
        self.assertEquals("toggl-api-key", config.entries[0].toggl)

        self.assertEquals("entry 2", config.entries[1].label)
        self.assertEquals("redmine-api-key2", config.entries[1].redmine)
        self.assertEquals("toggl-api-key2", config.entries[1].toggl)

    def test_fromFile_config3_no_url_in_mattermost(self):
        try:
            Config.fromFile("togglsync/tests/resources/config3.yml")
            self.fail()
        except Exception as exc:
            self.assertEqual('Expected "url" param in "mattermost" section', str(exc))

    def test_fromFile_no_toggl(self):
        try:
            Config.fromFile("togglsync/tests/resources/config4.yml")
            self.fail()
        except Exception as exc:
            self.assertEqual('"toggl" element not found in config', str(exc))

    def test_fromFile_no_redmine(self):
        try:
            Config.fromFile("togglsync/tests/resources/config5.yml")
            self.fail()
        except Exception as exc:
            self.assertEqual('One of "redmine" or "jira" is required in config', str(exc))

    def test_fromFile_no_entries(self):
        try:
            Config.fromFile("togglsync/tests/resources/config6.yml")
            self.fail()
        except Exception as exc:
            self.assertEqual('"entries" element not found in config', str(exc))

    def test_fromFile_config7_multiple_channels(self):
        config = Config.fromFile("togglsync/tests/resources/config7.yml")

        self.assertIsInstance(config.mattermost["channel"], list)

        self.assertEquals("#channell", config.mattermost["channel"][0])
        self.assertEquals("#channel2", config.mattermost["channel"][1])

    def test_fromFile_config8_multiple_channels(self):
        config = Config.fromFile("togglsync/tests/resources/config8.yml")

        self.assertIsInstance(config.mattermost["channel"], list)

        self.assertEquals("", config.mattermost["channel"][0])
        self.assertEquals("#channel2", config.mattermost["channel"][1])

    def test_fromFile_config9_jira_params(self):
        config = Config.fromFile("togglsync/tests/resources/config_jira.yml")

        self.assertEquals("https://www.toggl.com/api/v8/", config.toggl)
        self.assertEquals("http://jira.url/", config.jira)

        self.assertEquals(2, len(config.entries))

        self.assertEquals("redmine 1", config.entries[0].label)
        self.assertEquals("redmine-api-key", config.entries[0].redmine)
        self.assertEquals("toggl-api-key", config.entries[0].toggl)

        self.assertEquals("jira 1", config.entries[1].label)
        self.assertEquals("jira_username", config.entries[1].jira_username)
        self.assertEquals("toggl-api-key2", config.entries[1].toggl)


if __name__ == "__main__":
    unittest.main()
