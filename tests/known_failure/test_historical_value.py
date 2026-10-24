
from decimal import Decimal
from fixture import example_events
from ledger import Ledger
import unittest


class KnownDesignLimitation(unittest.TestCase):
    def test_historical_balance_snapshot(self):
        ledger = Ledger()

        # Process E1 through E10.
        for event in example_events():
            ledger.process(event)

        # EXPECTED CAPABILITY:
        # Query Day 2 as it was known at the end of Day 5.
        # E7 was present, but E9 had not yet arrived.
        #
        # DESIGN LIMITATION:
        # Current balance() uses all postings, including
        # E9's later reversal, so it cannot reconstruct
        # an earlier knowledge snapshot without an
        # additional processing-time filter.

        self.assertEqual(
            ledger.balance("ACC-001", 2),
            Decimal("-395.00")
        )
        
if __name__ == "__main__":
    unittest.main()