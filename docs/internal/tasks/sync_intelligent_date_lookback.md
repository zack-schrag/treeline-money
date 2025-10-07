Currently it appears that the /sync command always syncs 90 days of data. Instead, it should only sync 90 days on initial setup (when no transactions exist in the database). Otherwise, it should sync on the most recent date of the latest transaction in the DB minus 7 days. 

Optionally, it should provide an option to the user to specify start and end date (max 90 days ago). This should not require input and should not put any additional friction for the user.

Acceptance criteria:
- Sync 90 days on setup, otherwise latest transaction minus 7 days. For example, if the latest transaction is 2025-07-14, it should sync since 2025-07-07.
- Add option to sync based on optional start and end date
- This is business logic and should happen in the SyncService, NOT in the SimpleFIN provider. The SimpleFIN can accept the parameters (via the abstraction) but NOT as a special case. This needs to have it passed through the service layer appropriately.