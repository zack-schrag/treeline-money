Currently, we only get the latest balance snapshots during a /sync, and this is problematic on setup.

For example, I may have 90 days of SimpleFIN data, and 2 years of imported CSV data, but I only have the latest day's worth of balance snapshots!

We want to support a way for users to infer their balance history by back calculating their balances from their transaction history.

For example, let's say the user configures their setup and they have account A with current balance of $5000 and a history of 180 days of transaction data. Based on this information, we should be able to go back each of those 180 days and calculate the estimated balance for that day.

The risks:
- This won't be 100% accurate, it's an estimate
- If you're missing transactions, this could be wildly off

The pros:
- Users don't have to manually backfill balance entries to imemdiately get the benefits of something like a net worth tracker as soon as they import data.
- Most users probably don't care about a high degree of accuracy, an estimate is probably fine in most cases.

To mitigate the risks, we can provide ample warning to users about the drawbacks of this approach and warn them it's just an estimate.

Acceptance criteria:
- During /sync and/or initial setup, provide the user with an option to backfill balances. Probably only during the initial setup, not when /sync detects existing transactions
- Add a dedicated /backfill command
- Follow all TDD and hexagonal principles described in detail from the power_session document.