# Rejected acceptance criteria and design avenues

Four supplied assertions are **refused as written**. The other four are supported (with the indicated interpretation).

## "E7 causes exactly one overdraft fee to be assessed, on Day 2."

At the E7 checkpoint, and before any fees, value-date balances are Day 2 **AED -370.00**, Day 3 **AED +30.00**, Day 4 **AED -155.00**, Day 5 **AED -155.00**. The Day-2 fee then carries into future closing balances; Day 3 stays positive (AED +5.00), while Days **4 and 5 remain negative**. The fee conditions therefore assess AED 25.00 for **Days 2, 4, and 5**. “Once per day” is not “once per event.” E9 later generates correcting fee credits but cannot erase these historical assessments.

## Incorrect: "The three BHD instalments in E10 must each be BHD 3.334."

That sums to **BHD 10.002**, creating unearned BHD 0.002. Equal division at three-decimal currency precision is impossible. The implementation uses BHD **3.333 + 3.333 + 3.334 = 10.000** and chooses to assign residual units to the last installment.

## Incorrect: "If the rounded daily interest accruals do not sum to the capitalized total, the remainder is discarded."

This contradicts the non-negotiable requirement that the **sum of rounded daily accruals exactly equal the capitalized posting**. We calculate `capitalization = sum(rounded_daily_accruals)`, not round a separate six-day raw-interest total and throw away differences. On this stream: **AED 1.03** and **BHD 0.008**.
