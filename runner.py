"""Execute the stream and print final restated daily reports plus audit evidence."""
from decimal import Decimal
from fixture import example_events
from ledger import Ledger, FINAL_DAY


def main() -> None:
    ledger = Ledger()
    for event in example_events():
        result = ledger.process(event)
        print(f"  {event.event_id:>3} booked Day {event.booking_day}, "
              f"value Day {event.value_day}: {result.status} — {result.message}")
        if event.event_id == "E7":
            print("  E7 checkpoint, Day 2 BEFORE fees:",
                  f"AED {ledger.balance_before_fees('ACC-001', 2):.2f}")
            days = [d for d in range(1, FINAL_DAY + 1)
                    if any(p.kind == "OVERDRAFT_FEE" for p in ledger.fee_postings("ACC-001", d))]
            print("  E7 checkpoint, assessed fee value dates:", ", ".join(f"Day {d}" for d in days))
    accruals = ledger.capitalize_interest()
    print("\nFINAL RESTATED DAY REPORT (after every event; fee adjustments retained)")
    print("Balances include postings with value_day <= displayed day. "
          "Day 6 includes end-of-day capitalization.")
    for day in range(1, FINAL_DAY + 1):
        print(f"\nDAY {day}")
        for account_id, account in ledger.accounts.items():
            amount = ledger.balance(account_id, day)
            fees = ledger.fee_postings(account_id, day)
            fee_desc = ", ".join(
                f"{p.kind} {p.amount:+.{2 if account.currency == 'AED' else 3}f}"
                for p in fees) or "none"
            accrual = accruals[account_id][day - 1]
            print(f"  {account_id} {account.currency}: closing {amount}; "
                  f"interest accrued {accrual}; fees [{fee_desc}]")
        state = ledger.authorization_states(day)
        print("  authorizations:", ", ".join(f"{k}={v}" for k, v in sorted(state.items())) or "none")
        errors = ledger.errors_for_day(day)
        print("  errors:", "; ".join(f"{e.event_id}: {e.message}" for e in errors) or "none")
    print("\nDAY 6 CAPITALIZATION (sum of rounded daily accruals)")
    for account_id, account in ledger.accounts.items():
        total = sum(accruals[account_id], Decimal(0))
        posting = next(p for p in ledger.postings if p.account_id == account_id
                       and p.kind == "INTEREST_CAPITALIZATION")
        print(f"  {account_id} {account.currency}: daily {accruals[account_id]}, "
              f"sum {total}, posted {posting.amount}")
    print("\nE10 BHD installments:", [str(p.amount) for p in ledger.postings
          if p.source_event == "E10" and p.kind == "CREDIT"])


if __name__ == "__main__":
    main()
