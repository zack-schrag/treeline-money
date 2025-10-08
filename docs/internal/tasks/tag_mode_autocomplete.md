In /tag mode, a user can manually type a tag to enter. We should add autocomplete support for this (we already have autocomplete in a few features, make sure to review /import and the slash command autocomplete from the main prompt).

Acceptance criteria:
- As user types, tags are suggested in the autocomplete display. For example, if a user types "g", it might display something like "groceries" or "gas" if the user has existing tags for those.
- If this requires an architectural or in-depth change or a DB schema change, make sure to notify the user and come up with a proposal instead of implementing. The proposal can live in docs/internal/proposals.