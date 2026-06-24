"""venue.from_official wires the extracted happy-hour window into `hours`."""

import unittest

from pipeline.core import fetch, venue


class HappyHourWindowWiring(unittest.TestCase):
    def setUp(self):
        self._orig = fetch.get_text

    def tearDown(self):
        fetch.get_text = self._orig

    def _stub(self, html: str):
        fetch.get_text = lambda url: html  # noqa: ARG005

    def test_hh_window_populates_hours(self):
        self._stub("<html><body><h1>Lanai Bar</h1>"
                   "<p>Join us for Happy Hour Mon-Fri 3-6pm with kama'aina pricing.</p>"
                   "</body></html>")
        rec = venue.from_official(
            "https://example.com", category="food",
            subcategory="happy_hour", neighborhood="Waikiki", name="Lanai Bar")
        self.assertEqual(rec["hours"], "Mon-Fri 3-6pm")
        self.assertEqual(rec["status"], "active")

    def test_no_window_still_active_via_specials_fallback(self):
        self._stub("<html><body><p>We offer happy hour specials.</p></body></html>")
        rec = venue.from_official(
            "https://example.com", category="food",
            subcategory="happy_hour", neighborhood="Waikiki", name="Some Bar")
        self.assertNotIn("hours", rec)               # nothing fabricated
        self.assertEqual(rec["discount"], "happy hour specials")
        self.assertEqual(rec["status"], "active")


if __name__ == "__main__":
    unittest.main()
