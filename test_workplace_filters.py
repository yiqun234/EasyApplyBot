import unittest

from linkedineasyapply import LinkedinEasyApply


def base_parameters(**overrides):
    parameters = {
        "remote": False,
        "hybrid": False,
        "lessthanTenApplicants": False,
        "newestPostingsFirst": False,
        "experienceLevel": {
            "entry": True,
            "associate": False,
        },
        "distance": 100,
        "jobTypes": {
            "full-time": True,
            "contract": False,
        },
        "date": {
            "all time": True,
            "month": False,
            "week": False,
            "24 hours": False,
        },
    }
    parameters.update(overrides)
    return parameters


class WorkplaceFilterTests(unittest.TestCase):
    def setUp(self):
        self.bot = LinkedinEasyApply.__new__(LinkedinEasyApply)

    def test_remote_only_uses_linkedin_remote_workplace_filter(self):
        url = self.bot.get_base_search_url(base_parameters(remote=True))

        self.assertIn("f_WT=2", url)
        self.assertNotIn("f_WT=3", url)

    def test_hybrid_only_uses_linkedin_hybrid_workplace_filter(self):
        url = self.bot.get_base_search_url(base_parameters(hybrid=True))

        self.assertIn("f_WT=3", url)
        self.assertNotIn("f_WT=2", url)

    def test_remote_and_hybrid_can_be_combined(self):
        url = self.bot.get_base_search_url(base_parameters(remote=True, hybrid=True))

        self.assertIn("f_WT=2%2C3", url)

    def test_no_workplace_filter_when_remote_and_hybrid_are_false(self):
        url = self.bot.get_base_search_url(base_parameters())

        self.assertNotIn("f_WT=", url)


if __name__ == "__main__":
    unittest.main()
