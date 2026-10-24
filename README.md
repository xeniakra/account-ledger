# In-memory account ledger — Days 1–6

Pure Python 3.10+; standard library only (`decimal`, `dataclasses`, `unittest`). No server, UI, database, persistence, exchange-rate service, or third-party dependencies.

## Run

From the repository root:

```sh
python runner.py
```

The script replays **E1 through E10 in the specified order**, prints each decision, captures the **E7 before-fee Day-2 balance** and fee-day checkpoint, and then prints a report for **each Day 1–Day 6**. Each report includes both currencies' closing balances, rounded daily interest, all fee assessments/adjustments with that value date, authorization states, and event errors.

**Read the report as a final restated view:** amounts for Day `d` sum all postings with `value_day <= d` **after the full input has arrived**. This is not necessarily the information known at real-time close of Day `d`; E7 is backdated, and E10 has a Day-5 booking date but appears after Day-6 event E9 in input order. Authorization decisions are **not** restated; their recorded statuses are shown by the booking date of the deciding event. Day-6 closing ledger balances include interest capitalization at the end of Day 6; the displayed Day-6 interest accrual uses the pre-capitalization closing balance.

To run the *one intentionally failing* diagnostic separately (returns nonzero):

```sh
python -m unittest discover -s known_failure -v
```

That test is deliberately NOT part of the passing core suite. Its inline annotation explains why demanding retroactive approval of Auth-B would violate this design's decision-audit model. The diagnostic failure is acknowledged, not hidden or marked `expectedFailure`.

To inspect the intact Git history:

```sh
git log --oneline --reverse
```

## Results (final restated view)

| Day | ACC-001 closing AED | ACC-002 closing BHD | Auth states | Errors |
|---:|---:|---:|---|---|
| 1 | 250.00 | 0.000 | none | none |
| 2 | 250.00 | 0.000 | Auth-A APPROVED | none |
| 3 | 650.00 | 0.000 | Auth-A APPROVED | none |
| 4 | 465.00 | 0.000 | Auth-A SETTLED | E6, unknown Auth-Z |
| 5 | 465.00 | 10.000 | Auth-A SETTLED; Auth-B DECLINED | none |
| 6 | 466.03 | 10.008 | Auth-A SETTLED; Auth-B DECLINED | none |

E7 temporarily restates pre-fee Day 2 from AED `250.00` to AED `-370.00`. It assesses AED `25.00` with each of value dates Day 2, Day 4, Day 5. E9 then appends a compensating credit of AED `620.00` effective Day 2, and fee adjustments of AED `25.00` for each of those fee days. **The fee assessments remain in the journal**, with zero net outstanding fee after the adjustments. Settlement E5 debits AED `185.00` and releases the entire AED `200.00` hold. E6 is rejected without debiting money. Auth-B is declined at E8 and remains declined after E9.

Interest is rounded every day to its account currency quantum. The exact sum is capitalized **once** on Day 6: AED `1.03` on ACC-001 and BHD `0.008` on ACC-002. The three BHD postings are `3.333`, `3.333`, `3.334` (sum `10.000`).

## How the small design fits together

- `fixture.py`: immutable `Event` records in the **original** input order.
- `ledger.py`: immutable/frozen `Event`, `Posting`, and `Outcome` records. The journals append records only; public access returns tuples. Existing records are neither changed nor deleted.
- `runner.py`: deterministic stream playback and day-by-day report.
- `tests/test_ledger.py`: 15 passing tests for the specified behavior and invariants.
- `tests/known_failure/test_retroactive_auth.py`: one separately runnable, genuinely failing design-boundary test.
- `NUMBERS.md`: constants, units, precision, rationale.
- `AMBIGUITIES.md`: underspecified semantics and explicit choices.
- `REJECTED.md`: refused acceptance criteria and discarded approaches.
- `WORKLOG.md`: timestamped actions recorded during this build, in UTC.

The ledger is a **single-entry posting journal** for this exercise, not a full double-entry general ledger. A real bank would also require balanced GL offsets, idempotency/retries across processes, concurrency control, durable transaction boundaries, richer settlement statuses, reconciliations, and closed-period policies. No such capabilities are claimed here.
