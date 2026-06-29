"""Tests for deterministic happy-hour time-window extraction."""

import unittest

from pipeline.core import extract


class FindHappyHourWindow(unittest.TestCase):
    def test_time_range_after_keyword(self):
        t = "Stop by for Happy Hour, 3-6pm, in our bar every evening."
        self.assertEqual(extract.find_happy_hour_window(t), "3-6pm")

    def test_leading_day_phrase_is_included(self):
        t = "Happy Hour Mon-Fri 4–7 PM at the lounge."
        self.assertEqual(extract.find_happy_hour_window(t), "Mon-Fri 4–7 PM")

    def test_pau_hana_with_to_range(self):
        t = "Pau Hana 2 to 5 pm. Mahalo!"
        self.assertEqual(extract.find_happy_hour_window(t), "2 to 5 pm")

    def test_prefers_range_closest_to_a_keyword(self):
        # A loose "Happy Hour Menus" header sits near the pool bar's OPEN hours;
        # the specific "Happy Hour" right before the real range must win.
        t = ("All Day + Happy Hour Menus. Pool Bar 12-10 PM. "
             "Daily Happy Hour 12-6 PM. Restaurant 12-9 PM.")
        self.assertEqual(extract.find_happy_hour_window(t), "12-6 PM")

    def test_does_not_treat_sunset_as_a_weekday(self):
        # "Sunset" must not be misread as "Sun" (Sunday) and prepended.
        t = "Happy Hour Sunset 3:30pm - 6:00pm"
        self.assertEqual(extract.find_happy_hour_window(t), "3:30pm - 6:00pm")

    def test_none_when_no_explicit_range(self):
        # "happy hour specials" with no time window -> nothing to add.
        self.assertIsNone(extract.find_happy_hour_window("Happy hour specials available daily."))

    def test_none_when_time_is_far_from_keyword(self):
        # A dinner time elsewhere must not be grabbed as the happy-hour window.
        t = "Dinner service 5-9pm nightly. " + ("Lorem ipsum dolor sit amet. " * 6) + "We also offer happy hour."
        self.assertIsNone(extract.find_happy_hour_window(t))

    def test_none_when_no_keyword(self):
        self.assertIsNone(extract.find_happy_hour_window("Open daily 11am-10pm for lunch and dinner."))


if __name__ == "__main__":
    unittest.main()
