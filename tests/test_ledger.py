"""Runnable tests for the accounting contract. `python -m unittest discover -s tests -v`."""
import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from fixture import example_events
from ledger import Event, Ledger


class LedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = Ledger()
        self.events = example_events()

    def run_through(self, event_id: str) -> Ledger:
        for event in self.events:
            self.ledger.process(event)
            if event.event_id == event_id:
                break
        return self.ledger

    def test_day_one_balance_and_day_two_auth_hold(self):
        l = self.run_through("E3")
        self.assertEqual(l.balance("ACC-001", 2), Decimal("250.00"))
        self.assertEqual(l.available("ACC-001", 2), Decimal("50.00"))
        self.assertEqual(l.authorization_states(2), {"Auth-A": "APPROVED"})
        self.assertFalse(any(p.source_event == "E3" for p in l.postings))

    def test_day_four_settlement_releases_full_hold_and_debits_actual_amount(self):
        l = self.run_through("E5")
        self.assertEqual(l.balance("ACC-001", 4), Decimal("465.00"))
        self.assertEqual(l.available("ACC-001", 4), Decimal("465.00"))
        self.assertEqual(l.authorization_states(4)["Auth-A"], "SETTLED")
        self.assertEqual([p.amount for p in l.postings if p.source_event == "E5"],
                         [Decimal("-185.00")])

    def test_unknown_auth_settlement_rejected_without_money_moving(self):
        l = self.run_through("E6")
        self.assertEqual(l.outcomes[5].status, "REJECTED")
        self.assertIn("Auth-Z", l.outcomes[5].message)
        self.assertEqual(l.balance("ACC-001", 4), Decimal("465.00"))
        self.assertFalse(any(p.source_event == "E6" and p.amount != 0 for p in l.postings))

    def test_e7_day_two_pre_fee_and_multiple_fee_assessments(self):
        l = self.run_through("E7")
        self.assertEqual(l.balance_before_fees("ACC-001", 2), Decimal("-370.00"))
        self.assertEqual(l.balance("ACC-001", 2), Decimal("-395.00"))
        self.assertEqual(l.balance("ACC-001", 3), Decimal("5.00"))
        self.assertEqual(l.balance("ACC-001", 4), Decimal("-205.00"))
        self.assertEqual(l.balance("ACC-001", 5), Decimal("-230.00"))
        fee_days = [d for d in range(1, 6) if any(
            p.kind == "OVERDRAFT_FEE" for p in l.fee_postings("ACC-001", d))]
        self.assertEqual(fee_days, [2, 4, 5])

    def test_e8_declined_and_e9_does_not_redo_its_decision(self):
        l = self.run_through("E9")
        self.assertEqual(l.authorization_states(6)["Auth-B"], "DECLINED")
        self.assertEqual(l.outcomes[7].status, "DECLINED")
        self.assertEqual(l.balance("ACC-001", 5), Decimal("465.00"))
        self.assertEqual(l.available("ACC-001", 5), Decimal("465.00"))

    def test_reversal_appends_adjustments_and_retains_charges(self):
        self.run_through("E7")
        original = self.ledger.postings
        self.ledger.process(self.events[7])
        self.ledger.process(self.events[8])
        self.assertEqual(self.ledger.postings[:len(original)], original)
        self.assertTrue(any(p.source_event == "E7" for p in self.ledger.postings))
        for day in (2, 4, 5):
            entries = self.ledger.fee_postings("ACC-001", day)
            self.assertEqual([e.kind for e in entries], ["OVERDRAFT_FEE", "FEE_ADJUSTMENT"])
            self.assertEqual(sum((e.amount for e in entries), Decimal(0)), Decimal("0.00"))

    def test_authorizations_are_historical_immutable_decisions(self):
        l = self.run_through("E9")
        self.assertEqual(l.authorization_states(2), {"Auth-A": "APPROVED"})
        self.assertEqual(l.authorization_states(4), {"Auth-A": "SETTLED"})
        self.assertEqual(l.authorization_states(5)["Auth-B"], "DECLINED")
        self.assertEqual(l.authorization_states(6)["Auth-B"], "DECLINED")

    def test_bhd_installments_preserve_exact_amount_and_precision(self):
        l = self.run_through("E10")
        amounts = [p.amount for p in l.postings if p.source_event == "E10" and p.kind == "CREDIT"]
        self.assertEqual(amounts, [Decimal("3.333"), Decimal("3.333"), Decimal("3.334")])
        self.assertEqual(sum(amounts), Decimal("10.000"))
        self.assertEqual(l.balance("ACC-002", 5), Decimal("10.000"))

    def test_end_of_day_six_interest_exact_daily_sum_and_balances(self):
        l = self.run_through("E10")
        accruals = l.capitalize_interest()
        self.assertEqual(accruals["ACC-001"], tuple(map(Decimal,
                         ("0.10", "0.10", "0.26", "0.19", "0.19", "0.19"))))
        self.assertEqual(accruals["ACC-002"], tuple(map(Decimal,
                         ("0.000", "0.000", "0.000", "0.000", "0.004", "0.004"))))
        for account_id in l.accounts:
            caps = [p for p in l.postings if p.account_id == account_id
                    and p.kind == "INTEREST_CAPITALIZATION"]
            self.assertEqual(len(caps), 1)
            self.assertEqual(caps[0].amount, sum(accruals[account_id], Decimal(0)))
        self.assertEqual(l.balance("ACC-001", 6), Decimal("466.03"))
        self.assertEqual(l.balance("ACC-002", 6), Decimal("10.008"))
        n = len(l.postings)
        l.capitalize_interest()
        self.assertEqual(len(l.postings), n, "Capitalization must be idempotent")

    def test_transaction_arrival_order_is_preserved_not_sorted(self):
        l = self.run_through("E10")
        self.assertEqual([e.event_id for e in l.events],
                         [f"E{n}" for n in range(1, 11)])
        self.assertEqual(l.events[-1].booking_day, 5)
        self.assertEqual(l.events[-2].booking_day, 6)

    def test_duplicate_event_id_is_not_posted_twice(self):
        l = self.run_through("E1")
        with self.assertRaises(ValueError):
            l.process(self.events[0])
        self.assertEqual(len(l.events), 1)
        self.assertEqual(l.balance("ACC-001", 1), Decimal("1200.00"))

    def test_journal_records_are_frozen_and_never_deleted(self):
        l = self.run_through("E9")
        with self.assertRaises(FrozenInstanceError):
            l.postings[0].amount = Decimal(0)
        with self.assertRaises(FrozenInstanceError):
            l.events[0].amount = Decimal(0)
        self.assertGreater(len(l.postings), len(l.events))

    def test_hold_exact_zero_available_is_approved(self):
        l = Ledger()
        l.process(Event("T1", 1, "CREDIT", "ACC-001", 1, Decimal("20.00")))
        result = l.process(Event("T2", 1, "AUTHORIZATION", "ACC-001", 1,
                                 Decimal("20.00"), auth_id="H"))
        self.assertEqual(result.status, "APPROVED")
        self.assertEqual(l.available("ACC-001", 1), Decimal("0.00"))

    def test_settlement_over_hold_rejected(self):
        l = self.run_through("E3")
        result = l.process(Event("EXTRA", 3, "SETTLEMENT", "ACC-001", 3,
                                 Decimal("201.00"), auth_id="Auth-A"))
        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(l.authorization_states(3)["Auth-A"], "APPROVED")

    def test_post_finalization_rejects_new_events(self):
        l = self.run_through("E10")
        l.capitalize_interest()
        with self.assertRaises(RuntimeError):
            l.process(Event("LATE", 6, "CREDIT", "ACC-001", 6, Decimal("1.00")))


if __name__ == "__main__":
    unittest.main()
