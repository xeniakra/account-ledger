"""Append-only in-memory ledger for the six-day exercise (stdlib only)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional


INTEREST_RATE = Decimal("0.0004")  # 0.04%, not 0.04 as a fraction.
OVERDRAFT_FEE_AED = Decimal("25.00")
FINAL_DAY = 6
PRECISIONS = {"AED": Decimal("0.01"), "BHD": Decimal("0.001")}


@dataclass(frozen=True)
class Account:
    account_id: str
    currency: str
    opening: Decimal


@dataclass(frozen=True)
class Event:
    event_id: str
    booking_day: int
    kind: str
    account_id: str
    value_day: int
    amount: Decimal
    auth_id: Optional[str] = None
    reverses: Optional[str] = None
    installments: int = 1


@dataclass(frozen=True)
class Posting:
    posting_id: str
    kind: str
    account_id: str
    booking_day: int
    value_day: int
    amount: Decimal  # Signed: credit positive, debit negative.
    source_event: str
    reference: Optional[str] = None


@dataclass(frozen=True)
class Outcome:
    event_id: str
    status: str
    message: str


class Ledger:
    def __init__(self) -> None:
        self.accounts = {
            "ACC-001": Account("ACC-001", "AED", Decimal("0.00")),
            "ACC-002": Account("ACC-002", "BHD", Decimal("0.000")),
        }
        self._events: list[Event] = []
        self._outcomes: list[Outcome] = []
        self._postings: list[Posting] = []
        self._interest: dict[str, tuple[Decimal, ...]] = {}
        self._finalized = False

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events)

    @property
    def outcomes(self) -> tuple[Outcome, ...]:
        return tuple(self._outcomes)

    @property
    def postings(self) -> tuple[Posting, ...]:
        return tuple(self._postings)

    def _quantum(self, account_id: str) -> Decimal:
        return PRECISIONS[self.accounts[account_id].currency]

    def _round(self, account_id: str, amount: Decimal) -> Decimal:
        return amount.quantize(self._quantum(account_id), rounding=ROUND_HALF_UP)

    def _post(self, kind: str, account_id: str, booking_day: int,
              value_day: int, amount: Decimal, source: str,
              reference: Optional[str] = None) -> Posting:
        rounded = self._round(account_id, amount)
        assert rounded == amount, f"Posting not in currency precision: {amount}"
        posting = Posting(f"P{len(self._postings) + 1:04d}", kind, account_id,
                          booking_day, value_day, rounded, source, reference)
        self._postings.append(posting)
        return posting

    def balance(self, account_id: str, day: int,
                *, include_capitalization: bool = True) -> Decimal:
        account = self.accounts[account_id]
        return account.opening + sum((p.amount for p in self._postings
            if p.account_id == account_id and p.value_day <= day
            and (include_capitalization or p.kind != "INTEREST_CAPITALIZATION")), Decimal(0))

    def balance_before_fees(self, account_id: str, day: int) -> Decimal:
        """For inspecting E7's impact without charges/refunds or interest."""
        return self.accounts[account_id].opening + sum(
            (p.amount for p in self._postings if p.account_id == account_id
             and p.value_day <= day and p.kind not in
             {"OVERDRAFT_FEE", "FEE_ADJUSTMENT", "INTEREST_CAPITALIZATION"}),
            Decimal(0))

    def authorization_states(self, day: int = FINAL_DAY) -> dict[str, str]:
        states: dict[str, str] = {}
        # Decisions were made at arrival time and are NEVER retrospectively redone.
        for event, result in zip(self._events, self._outcomes):
            if event.booking_day > day:
                continue
            if event.kind == "AUTHORIZATION" and event.auth_id:
                states[event.auth_id] = result.status
            elif event.kind == "SETTLEMENT" and event.auth_id and result.status == "POSTED":
                states[event.auth_id] = "SETTLED"
        return states

    def _auth_original(self, auth_id: str) -> tuple[Event, str] | None:
        for event, result in zip(self._events, self._outcomes):
            if event.kind == "AUTHORIZATION" and event.auth_id == auth_id:
                return event, result.status
        return None

    def _active_holds(self, account_id: str, day: int) -> Decimal:
        states = self.authorization_states(day)
        return sum((e.amount for e in self._events if e.kind == "AUTHORIZATION"
                    and e.account_id == account_id and e.booking_day <= day
                    and states.get(e.auth_id) == "APPROVED"), Decimal(0))

    def available(self, account_id: str, day: int) -> Decimal:
        return self.balance(account_id, day) - self._active_holds(account_id, day)

    def _reject(self, event: Event, reason: str) -> Outcome:
        # A failed event also stays in the input log, and has an immutable error record.
        self._post("ERROR", event.account_id, event.booking_day, event.value_day,
                   self._round(event.account_id, Decimal(0)), event.event_id)
        result = Outcome(event.event_id, "REJECTED", reason)
        self._outcomes.append(result)
        return result

    def _record_outcome(self, event: Event, status: str, message: str) -> Outcome:
        result = Outcome(event.event_id, status, message)
        self._outcomes.append(result)
        return result

    def _split(self, event: Event) -> tuple[Decimal, ...]:
        """As-even-as-possible allocation; any residual smallest units go last."""
        unit = self._quantum(event.account_id)
        n = event.installments
        base = (event.amount / n).quantize(unit, rounding=ROUND_DOWN)
        residual_units = int((event.amount - base * n) / unit)
        result = [base] * n
        for index in range(n - residual_units, n):
            result[index] += unit
        assert sum(result) == event.amount
        return tuple(result)

    def process(self, event: Event) -> Outcome:
        if self._finalized:
            raise RuntimeError("Capitalization is final; no more events accepted")
        if any(e.event_id == event.event_id for e in self._events):
            raise ValueError(f"Duplicate event identifier: {event.event_id}")
        if event.account_id not in self.accounts:
            raise ValueError(f"Unknown account: {event.account_id}")
        if not (1 <= event.booking_day <= FINAL_DAY and 1 <= event.value_day <= FINAL_DAY):
            raise ValueError("Day must lie in the Day 1–Day 6 window")
        if event.amount <= 0 or self._round(event.account_id, event.amount) != event.amount:
            raise ValueError("Amounts must be positive and exactly representable")
        if event.installments < 1:
            raise ValueError("Installment count must be positive")
        self._events.append(event)

        if event.kind == "AUTHORIZATION":
            if not event.auth_id:
                return self._reject(event, "Missing authorization ID")
            if self._auth_original(event.auth_id) is not None:
                return self._reject(event, "Authorization ID already exists")
            remaining = self.available(event.account_id, event.booking_day) - event.amount
            if remaining < 0:
                return self._record_outcome(event, "DECLINED",
                                            f"Insufficient available funds; after hold: {remaining}")
            return self._record_outcome(event, "APPROVED",
                                        f"Hold {event.amount} reserved; available after hold: {remaining}")

        if event.kind == "SETTLEMENT":
            original = self._auth_original(event.auth_id or "")
            if original is None or original[1] != "APPROVED":
                return self._reject(event, f"Unknown or unapproved authorization {event.auth_id}")
            authorization = original[0]
            if authorization.account_id != event.account_id:
                return self._reject(event, "Settlement account does not match authorization")
            if self.authorization_states().get(event.auth_id) == "SETTLED":
                return self._reject(event, "Authorization already settled")
            if event.amount > authorization.amount:
                return self._reject(event, "Settlement exceeds authorized hold")
            self._post("SETTLEMENT", event.account_id, event.booking_day,
                       event.value_day, -event.amount, event.event_id,
                       reference=authorization.event_id)
            result = self._record_outcome(event, "POSTED", "Settlement posted; hold released")
            self.reconcile_fees(event.account_id, event.booking_day)
            return result

        if event.kind == "REVERSAL":
            target = next((e for e in self._events if e.event_id == event.reverses
                           and e is not event), None)
            original_result = next((o for o in self._outcomes if o.event_id == event.reverses), None)
            if target is None or original_result is None or original_result.status != "POSTED":
                return self._reject(event, "Reversal target absent or not posted")
            if target.account_id != event.account_id or target.kind not in {"CREDIT", "DEBIT"}:
                return self._reject(event, "Reversal target must be a posted credit/debit on this account")
            if event.value_day != target.value_day or event.amount != target.amount:
                return self._reject(event, "Reversal amount/value date must match original")
            if any(e.kind == "REVERSAL" and e.reverses == event.reverses
                   and o.status == "POSTED" for e, o in zip(self._events, self._outcomes)):
                return self._reject(event, "Original event already reversed")
            amount = event.amount if target.kind == "DEBIT" else -event.amount
            self._post("REVERSAL", event.account_id, event.booking_day,
                       event.value_day, amount, event.event_id, reference=event.reverses)
            result = self._record_outcome(event, "POSTED", "Compensating posting added; original retained")
            self.reconcile_fees(event.account_id, event.booking_day)
            return result

        if event.kind in {"CREDIT", "DEBIT"}:
            if event.installments > 1 and event.kind != "CREDIT":
                return self._reject(event, "Only credit installments supported in this exercise")
            sign = Decimal(1) if event.kind == "CREDIT" else Decimal(-1)
            for amount in self._split(event):
                self._post(event.kind, event.account_id, event.booking_day,
                           event.value_day, sign * amount, event.event_id)
            result = self._record_outcome(event, "POSTED", "Ledger postings appended")
            self.reconcile_fees(event.account_id, event.booking_day)
            return result

        return self._reject(event, f"Unsupported event type {event.kind}")

    def reconcile_fees(self, account_id: str, observed_through: int) -> None:
        """Derive the correct *outstanding* fee set; append charges/refunds only.

        Previous dates' fees affect subsequent dates' closing balances. When a
        backdated reversal eliminates a negative close, append a correcting fee
        credit on the ORIGINAL fee value day; never delete the old fee charge.
        """
        expected: set[int] = set()
        fee = OVERDRAFT_FEE_AED if self.accounts[account_id].currency == "AED" else None
        if fee is None:
            # Only AED fee specified; no BHD overdraft fee is invented.
            return
        for day in range(1, observed_through + 1):
            before = self.balance_before_fees(account_id, day) - fee * sum(
                d < day for d in expected)
            if before < 0:
                expected.add(day)
        for day in range(1, observed_through + 1):
            fee_entries = [p for p in self._postings if p.account_id == account_id
                           and p.value_day == day and p.kind in
                           {"OVERDRAFT_FEE", "FEE_ADJUSTMENT"}]
            outstanding = sum((p.amount for p in fee_entries), Decimal(0))
            if day in expected and outstanding == 0:
                self._post("OVERDRAFT_FEE", account_id, observed_through,
                           day, -fee, "SYSTEM-FEE")
            elif day not in expected and outstanding < 0:
                unrefunded = next((p for p in reversed(fee_entries)
                                   if p.kind == "OVERDRAFT_FEE"), None)
                self._post("FEE_ADJUSTMENT", account_id, observed_through,
                           day, -outstanding, "SYSTEM-FEE-CORRECTION",
                           reference=unrefunded.posting_id if unrefunded else None)
            elif outstanding not in {Decimal(0), -fee}:
                raise AssertionError("Fee reconciliation invariant violated")

    def capitalize_interest(self) -> dict[str, tuple[Decimal, ...]]:
        if self._finalized:
            return dict(self._interest)
        # Accrue on the ledger before capitalization, not on the capitalization itself.
        for account_id in self.accounts:
            daily: list[Decimal] = []
            for day in range(1, FINAL_DAY + 1):
                basis = self.balance(account_id, day, include_capitalization=False)
                daily.append(self._round(account_id, max(basis, Decimal(0)) * INTEREST_RATE))
            self._interest[account_id] = tuple(daily)
            total = sum(daily, Decimal(0))  # NEVER discard rounding residuals.
            if total:
                self._post("INTEREST_CAPITALIZATION", account_id, FINAL_DAY,
                           FINAL_DAY, total, "SYSTEM-INTEREST")
        self._finalized = True
        return dict(self._interest)

    @property
    def daily_interest(self) -> dict[str, tuple[Decimal, ...]]:
        return dict(self._interest)

    def fee_postings(self, account_id: str, day: int) -> tuple[Posting, ...]:
        return tuple(p for p in self._postings if p.account_id == account_id
                     and p.value_day == day and p.kind in
                     {"OVERDRAFT_FEE", "FEE_ADJUSTMENT"})

    def errors_for_day(self, day: int) -> tuple[Outcome, ...]:
        return tuple(outcome for event, outcome in zip(self._events, self._outcomes)
                     if event.booking_day == day and outcome.status == "REJECTED")
