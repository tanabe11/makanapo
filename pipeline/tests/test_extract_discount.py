"""Tests for deterministic discount extraction (find_discount)."""

import unittest

from pipeline.core import extract


class FindDiscount(unittest.TestCase):
    def test_lead_offer_when_dollar_offers_run_together(self):
        # Menu offers concatenated with no separators must not merge into one
        # unreadable run-on — capture just the lead offer.
        t = "Happy hour: $2 Off All Beers$3 Off Select Cocktails50% Off Select Apps$14 Pizzas"
        self.assertEqual(extract.find_discount(t), "$2 Off All Beers")

    def test_percent_offer_unchanged(self):
        t = "Enjoy 18% off all pasta and appetizers during happy hour."
        self.assertEqual(extract.find_discount(t), "18% off all pasta and appetizers during happy hour")

    def test_single_dollar_offer_kept(self):
        self.assertEqual(extract.find_discount("Get $5 off your first order"), "$5 off your first order")

    def test_bogo(self):
        self.assertEqual(extract.find_discount("BOGO on all entrees"), "BOGO")


if __name__ == "__main__":
    unittest.main()
