import unittest

from togglsync.config import Config
from togglsync.config import Entry


class EntryTests(unittest.TestCase):
    def str_test_redmine(self):
        e = Entry("", "<redmine>", "<toggl>")
        self.assertEquals("<toggl>: <redmine>", str(e))

    def str_test_jira(self):
        e = Entry("", None, "<toggl>", "jira_user", jira_url="http://jira.url")
        self.assertEquals("<toggl>: jira_user@http://jira.url", str(e))


class ConfigTests(unittest.TestCase):
    def test_fromFile_config1(self):
        config = Config.fromFile("togglsync/tests/resources/config1.yml")

        self.assertEquals("https://www.toggl.com/api/v8/", config.toggl)
        self.assertEquals("http://redmine.url/", config.redmine)
        self.assertEquals("http://mattermost.url/", config.mattermost["url"])

        self.assertEquals(2, len(config.entries))

        self.assertEquals("entry 1", config.entries[0].label)
        self.assertEquals("redmine-api-key", config.entries[0].redmine_api_key)
        self.assertEquals("toggl-api-key", config.entries[0].toggl)

        self.assertEquals("entry 2", config.entries[1].label)
        self.assertEquals("redmine-api-key2", config.entries[1].redmine_api_key)
        self.assertEquals("toggl-api-key2", config.entries[1].toggl)

    def test_fromFile_config2(self):
        config = Config.fromFile("togglsync/tests/resources/config2.yml")

        self.assertEquals("https://www.toggl.com/api/v8/", config.toggl)
        self.assertEquals("http://redmine.url/", config.redmine)
        self.assertEquals("http://mattermost.url/", config.mattermost["url"])
        self.assertEquals("#channell", config.mattermost["channel"])

        self.assertEquals(2, len(config.entries))

        self.assertEquals("entry 1", config.entries[0].label)
        self.assertEquals("redmine-api-key", config.entries[0].redmine_api_key)
        self.assertEquals("toggl-api-key", config.entries[0].toggl)

        self.assertEquals("entry 2", config.entries[1].label)
        self.assertEquals("redmine-api-key2", config.entries[1].redmine_api_key)
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

        self.assertEquals(3, len(config.entries))

        self.assertEquals("redmine 1", config.entries[0].label)
        self.assertEquals("redmine-api-key", config.entries[0].redmine_api_key)
        self.assertEquals("toggl-api-key", config.entries[0].toggl)
        self.assertEquals("pattern A", config.entries[0].task_patterns[0])

        self.assertEquals("Jira 1", config.entries[1].label)
        self.assertEquals("http://jira1.url/", config.entries[1].jira_url)
        self.assertEquals("jira_username", config.entries[1].jira_username)
        self.assertEquals("toggl-api-key1", config.entries[1].toggl)
        self.assertEquals("pattern B", config.entries[1].task_patterns[0])
        self.assertEquals("pattern C", config.entries[1].task_patterns[1])

        self.assertEquals("Jira 2", config.entries[2].label)
        self.assertEquals("http://jira2.url/", config.entries[2].jira_url)
        self.assertEquals("jira_username", config.entries[2].jira_username)
        self.assertEquals("toggl-api-key2", config.entries[2].toggl)
        self.assertEquals("pattern D", config.entries[2].task_patterns[0])
        self.assertEquals("pattern E", config.entries[2].task_patterns[1])


if __name__ == "__main__":
    unittest.main()
