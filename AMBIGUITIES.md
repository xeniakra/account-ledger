# Ambiguities and explicit resolutions

| Ambiguity | Resolution | Why it matters |
|---|---|---|

| **Meaning of closing Day D after a backdated event** | Reports are *restated after all events* using `value_day <= D`, not snapshots of knowledge physically available at Day D. | On Day 5, E7 restates the prior Day-2 balance. Both viewpoints are defensible but different. (/Users/xenia/Desktop/ledger/tests/known_failure/test_historical_value.py) |

| **Are overdraft fees defined for BHD?** | No BHD fee schedule or exchange rate exists. This exercise applies the specified **AED 25.00** fee only to the AED account; ACC-002 is never negative anyway. | Inventing BHD 25.000 or silently converting AED is unjustified. |


| **Can an authorization settle more than once?** | At most once in this exercise; further settlements rejected. | Prevents accidental duplicate debits without designing partial captures. |

| **Can an unknown settlement debit anyway?** | No; E6 creates an ERROR record with zero financial amount. | An absent authorization must not authorize money movement. |

| **What are errors vs. normal business declines?** | Structural violations (e.g. E6) are `REJECTED` and reported as errors; insufficient funds (E8) is a `DECLINED` auth state, not a processing error. | Keeps machine/business outcomes distinguishable. |

| **What counts as 'equal installments' when indivisible at currency precision?** | Minimize the discrepancy: take floor in smallest currency units and place remaining unit(s) in final installment(s). | `10.000 / 3` cannot be represented by three literally equal 3-decimal amounts. |

| **How is currency rounding done?** | `Decimal` throughout, input precision validated, `ROUND_HALF_UP` for calculated daily interest, explicit smallest-unit allocation for splits. | Floating point and implicit tie-breaking risk monetary inconsistencies. |

| **Is Day-6 interest earned on its own capitalization?** | No. Calculate Day-6 accrual on the closing ledger *before* Day-6 capitalization, then post the total. | Prevents circular interest-on-interest within the same day. |

| **Do restated daily interest amounts include backdated corrections?** | Yes. After all events arrive, recompute daily accruals for the final effective-date history, then capitalize once. | Earlier provisional accruals are not assumed immutable when nothing was booked yet. |

| **Duplicate external event IDs** | Reject outright with `ValueError`, without appending duplicate financial postings. | A minimal in-memory idempotency invariant, not a persistent delivery guarantee. |

| **Invalid fixture data** | Invalid days, account IDs, excessive decimal precision, and duplicate event IDs raise validation errors; accepted fixture failures such as E6 are journaled as outcomes. | The supplied stream is trusted as syntactically well-formed; distinction avoids pretending to build a production ingestion API. |

| **Double-entry accounting** | This is a single-account posting core, not a full general ledger with offsetting entries. | No cash/clearing/fee-income accounts were supplied, and inventing them would widen scope. |
