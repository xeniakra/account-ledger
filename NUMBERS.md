# Numbers, units, and “why not half?”

| Number / parameter | Source | Why this value, rather than half? |
|---|---|---|
| Account count **2**, ACC-001 and ACC-002 | Explicit stream | Half would omit a currency/account. Account labels are opaque IDs, not amounts. |
| Opening **0.00 AED** and **0.000 BHD** | Explicit stream | Half is also zero; the displayed scale is determined by currency precision. |
| Days **1–6**; `FINAL_DAY = 6` | Explicit window | Three days would exclude E5–E10 and interest capitalization. The lower bound is Day 1, not Day 0. |
| AED fractional digits **2**, quantum `0.01` | Explicit rule | Quantum `0.005` would permit amounts AED does not represent here. |
| BHD fractional digits **3**, quantum `0.001` | Explicit rule | Quantum `0.0005` would permit amounts BHD does not represent here. |
| Overdraft fee AED **25.00** per applicable day/account | Explicit rule | AED 12.50 would violate the contract. BHD-denominated overdraft fee is *not specified*, so the code does not guess a conversion. |
| Daily rate **0.04%** = decimal **0.0004** | Explicit rule | 0.02% would under-accrue interest; `0.04` as a fraction would be a 100× unit error. |
| Interest posting count **1**, at end of **Day 6** per account | Explicit rule | Half a posting is meaningless; six interest postings would contradict the capitalization instruction. |
| Nonnegative authorization threshold **0** after hold | Explicit rule | Zero is a boundary, not a tunable amount; *exactly zero* is approved. |
| `ROUND_HALF_UP` rounding mode | Implementation choice | The rules specify precision, not tie breaking. Half of a rounding mode has no meaning. Documented consistent rounding is better than implicit runtime rounding. |
| Splitting `10.000` across **3** BHD installments | Explicit E10 input | Using 1 or 2 installments violates the input. The exact repeating third requires residual allocation. |
| E10 BHD allocated `3.333`, `3.333`, `3.334` | Derived via integer smallest-unit distribution | Three equal `3.334` postings would create `10.002`; halving any installment would fail conservation. Last installment receives the residual smallest unit by convention. |
| Day-2 pre-fee E7 balance **−370.00 AED** | Derived: `1200 - 950 - 620` | Halving the debit/credit would alter the specified stream. |
| Fee-assessment days after E7: **2, 4, 5** | Derived from the entire affected closing history | One fee on Day 2 would ignore Days 4 and 5; a second fee on the same day would double-charge. |
| Day-6 AED interest **1.03**, BHD interest **0.008** | Derived from six rounded daily accruals | Discarding half or any residue violates equality of accrued and capitalized amounts. |
| Input events **10** (E1–E10), in supplied order | Explicit stream | Omitting half would skip reversals and multi-currency behavior. |
| Additional test-only credit **20.00**, matching hold **20.00** | Chosen to test exact-zero available funds | Half both would test the same equality; these simple equal values make the acceptance boundary readable. |
| Additional test-only settlement **201.00** vs hold **200.00** | Chosen to test just-over-hold rejection | 100.50 is below the held 200 and would not test exceeding the hold. |
| Additional test-only post-finalization credit **1.00** | Chosen only to attempt an invalid late mutation | Half would still be blocked; the amount does not control the rule, so 1.00 is simply the smallest convenient whole amount. |

Every other monetary amount and each booking/value date in `fixture.py` are direct copies of the user's E1–E10 stream, not free constants selected by the implementation. Posting IDs use zero-padded four-digit sequence numbers only as readable identifiers, not as accounting limits. There are no artificial caps or tolerances; `Decimal` performs exact base-10 arithmetic.
