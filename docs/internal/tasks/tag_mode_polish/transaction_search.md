Right now a user has to manually scroll through to find transactions in tag mode. Instead, we should allow them to search to filter.

Acceptance criteria:
- end user can filter transaction results in tag mode with searching to limit results
- the filtered results should still allow transaction tagging like normal.
- The search should not require user to hit "enter" to execute the search, it should search instantly as the user types.
- The TUI should display some sort of visual indicator that the search is loading. Since the DB is local, it should be very fast, but there could be edge cases where searching takes 1-2+ seconds.