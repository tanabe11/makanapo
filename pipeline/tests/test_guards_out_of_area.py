"""Tests for the off-Oahu guard (guards.out_of_area)."""

import unittest

from pipeline.core import guards


class OutOfArea(unittest.TestCase):
    def test_hawaii_zip_is_in_area(self):
        self.assertFalse(out := guards.out_of_area({"address": "2301 Kalakaua Ave, Honolulu, HI 96815"}), out)

    def test_mainland_zip_is_out_of_area(self):
        self.assertTrue(guards.out_of_area({"address": "123 Main St, Austin, TX 78701"}))

    def test_misextracted_leading_number_still_in_area(self):
        # A mangled street number ("22301" for 2301) must not be read as the ZIP
        # and drop a real Waikiki venue — the trailing 96815 marks it Oahu.
        self.assertFalse(guards.out_of_area({"address": "22301 Kalakaua Avenue, Honolulu, HI 96815"}))

    def test_offisland_coords_are_out_of_area(self):
        self.assertTrue(guards.out_of_area({"lat": 37.77, "lng": -122.42}))  # San Francisco

    def test_oahu_coords_are_in_area(self):
        self.assertFalse(guards.out_of_area({"lat": 21.28, "lng": -157.83}))

    def test_no_coords_no_zip_is_ambiguous_not_dropped(self):
        self.assertFalse(guards.out_of_area({"name": "Somewhere"}))


if __name__ == "__main__":
    unittest.main()
