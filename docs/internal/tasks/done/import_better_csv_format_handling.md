In import mode, we display a preview to the user like this:
```
Detecting CSV columns...

✓ Detected columns:
  date: Date
  debit: Debit
  credit: Credit
  description: Description

Loading preview...

Preview - First 5 Transactions:

 Date          Description                                        Amount 
 2025-10-03    PAYMENT THANK YOU                              $-133.73 
 2025-10-02    MCDONALD'S F11111 New York NY                     $23.22 
...

Does this look correct?
  Note: Negative amounts = spending, Positive = income/refunds

Proceed with import? [y/n] (y): n

What would you like to adjust?
  [1] Flip all signs (spending should be negative)
  [2] Try different column mapping
  [3] Cancel

Choice [1/2/3] (3): 
```
Instead of having two steps: "Proceed with import?" and "What would you like to adjust?" just have one step. Also the text copy needs better clarity that spending should be negative.

Acceptance criteria:
- 2 steps are condensed into one step with all options available.
- Text copy is more clear to the user that spending should be negative, so they can fix their imports if necessary.
- Allow user to optionally preview more than the first 5 transactions, they should be have an option to view another 5-10 transactions