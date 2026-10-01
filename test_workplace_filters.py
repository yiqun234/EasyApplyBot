import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, urlencode, urlparse

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


class SearchURLTests(unittest.TestCase):
    def setUp(self):
        self.bot = LinkedinEasyApply.__new__(LinkedinEasyApply)
        self.bot.browser = Mock()
        self.bot.avoid_lock = Mock()

    def build_page(self, parameters=None, keyword="Full stack engineer", page=0,
                   location="San Francisco", geo_id="102277331"):
        self.bot.base_search_url = self.bot.get_base_search_url(
            base_parameters() if parameters is None else parameters
        )
        fragment = urlencode({"location": location, "geoId": geo_id})
        self.bot.next_job_page(keyword, fragment, page)
        url = self.bot.browser.get.call_args.args[0]
        return url, parse_qs(urlparse(url).query)

    def test_full_url_has_one_question_mark_and_valid_distance(self):
        url, params = self.build_page()
        self.assertEqual(url.count("?"), 1)
        self.assertNotIn("&&", url)
        self.assertEqual(params["distance"], ["100"])
        self.assertNotIn("?distance", params)
        self.assertEqual(params["f_AL"], ["true"])
        self.assertEqual(params["keywords"], ["Full stack engineer"])
        self.bot.avoid_lock.assert_called_once()

    def test_keywords_and_locations_with_reserved_characters_round_trip(self):
        keyword = "C++ & React/Node.js # Engineer"
        location = "St. John's & Bay Area"
        _, params = self.build_page(keyword=keyword, location=location)
        self.assertEqual(params["keywords"], [keyword])
        self.assertEqual(params["location"], [location])
        self.assertEqual(params["geoId"], ["102277331"])

    def test_pagination_uses_zero_based_offsets(self):
        for page, start in ((0, "0"), (1, "25"), (2, "50"), (-1, "0")):
            with self.subTest(page=page):
                _, params = self.build_page(page=page)
                self.assertEqual(params["start"], [start])

    def test_empty_keywords_do_not_navigate(self):
        for keyword in ("", "  ", None):
            with self.subTest(keyword=keyword):
                with self.assertRaises(ValueError):
                    self.build_page(keyword=keyword)
        self.bot.browser.get.assert_not_called()

    def test_experience_codes_do_not_depend_on_config_order(self):
        for levels in (
            {"associate": True, "director": True, "entry": False,
             "executive": True, "internship": False, "mid-senior level": True},
            {"executive": True, "mid-senior level": True, "director": True,
             "associate": True, "internship": False, "entry": False},
        ):
            with self.subTest(levels=levels):
                _, params = self.build_page(base_parameters(experienceLevel=levels))
                self.assertEqual(params["f_E"], ["3,4,5,6"])

    def test_cloud_experience_aliases_do_not_add_extra_codes(self):
        _, params = self.build_page(base_parameters(experienceLevel={
            "associate": True, "director": True, "entry": False,
            "executive": True, "internship": False,
            "mid-senior level": True, "mid-senior_level": True,
        }))
        self.assertEqual(params["f_E"], ["3,4,5,6"])
        self.assertNotIn("7", params["f_E"][0])

    def test_false_cloud_alias_overrides_stale_legacy_value(self):
        _, params = self.build_page(base_parameters(
            experienceLevel={"associate": True, "mid-senior level": True,
                             "mid-senior_level": False},
            jobTypes={"full-time": True, "full_time": False, "contract": True},
            date={"24 hours": True, "24_hours": False, "all_time": True},
        ))
        self.assertEqual(params["f_E"], ["3"])
        self.assertEqual(params["f_JT"], ["C"])
        self.assertNotIn("f_TPR", params)

    def test_job_types_have_fixed_codes_and_accept_cloud_names(self):
        _, params = self.build_page(base_parameters(jobTypes={
            "other": True, "volunteer": True, "internship": True,
            "temporary": True, "contract": True, "part_time": True,
            "full_time": True, "unknown": True,
        }))
        self.assertEqual(params["f_JT"], ["F,P,C,T,I,V,O"])

    def test_cloud_date_wins_over_leftover_all_time_default(self):
        _, params = self.build_page(base_parameters(date={
            "24 hours": False, "24_hours": True,
            "all time": True, "all_time": False,
            "custom_hours": False, "month": False, "week": False,
        }))
        self.assertEqual(params["f_TPR"], ["r86400"])

    def test_legacy_date_filters_remain_supported(self):
        for key, seconds in (("24 hours", 86400), ("week", 604800), ("month", 2592000)):
            with self.subTest(key=key):
                _, params = self.build_page(base_parameters(date={key: True}))
                self.assertEqual(params["f_TPR"], [f"r{seconds}"])

    def test_conflicting_dates_choose_specific_filter_independent_of_order(self):
        for dates in (
            {"all time": True, "month": True, "24_hours": True},
            {"24_hours": True, "month": True, "all time": True},
        ):
            _, params = self.build_page(base_parameters(date=dates))
            self.assertEqual(params["f_TPR"], ["r86400"])

    def test_custom_hours_take_priority(self):
        _, params = self.build_page(base_parameters(
            date={"all time": True, "24_hours": True, "custom_hours": True},
            customHours=6,
        ))
        self.assertEqual(params["f_TPR"], ["r21600"])

    def test_invalid_custom_hours_fall_back_to_24_hours(self):
        for hours in (None, "invalid", 0, -1, True, float("inf")):
            with self.subTest(hours=hours):
                _, params = self.build_page(base_parameters(
                    date={"custom_hours": True}, customHours=hours,
                ))
                self.assertEqual(params["f_TPR"], ["r86400"])

    def test_missing_or_empty_optional_filters_are_omitted(self):
        for empty in (None, {}, []):
            with self.subTest(empty=empty):
                _, params = self.build_page(base_parameters(
                    date=empty, experienceLevel=empty, jobTypes=empty,
                ))
                for key in ("f_E", "f_JT", "f_TPR"):
                    self.assertNotIn(key, params)

    def test_invalid_distance_is_rejected_without_navigation(self):
        for distance in (True, -1, 1000, "invalid"):
            with self.subTest(distance=distance):
                with self.assertRaises(ValueError):
                    self.build_page(base_parameters(distance=distance))
        self.bot.browser.get.assert_not_called()

    def test_all_filters_survive_full_url_construction(self):
        _, params = self.build_page(base_parameters(
            remote=True, hybrid=True, lessthanTenApplicants=True,
            newestPostingsFirst=True, date={"24_hours": True},
        ))
        for key, value in {
            "f_WT": "2,3", "f_EA": "true", "sortBy": "DD",
            "f_E": "2", "f_JT": "F", "f_TPR": "r86400",
        }.items():
            self.assertEqual(params[key], [value])


if __name__ == "__main__":
    unittest.main()
