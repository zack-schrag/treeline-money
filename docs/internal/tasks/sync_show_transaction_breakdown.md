Currently, after sync it display something like this:
```
Synchronizing Financial Data

Syncing simplefin...
  ✓ Synced 9 account(s)
  Syncing transactions since 2025-09-29 (with 7-day overlap)
  ✓ Synced 47 transaction(s)
  Balance snapshots created automatically from account data

✓ Sync completed!

Use /status to see your updated data
```

Instead, we want a breakdown of the transactions based on if they were new, updated, or skipped due to being duplicates. Take a look at the /import command flow, it displays a good breakdown you can use.

Acceptance criteria:
- /sync flow shows transaction breakdown as described above.