In tag mode, a user can manually type a tag to enter, but right now it's a pop-up modal and lacks autocomplete.

We should:
- Add autocomplete support
- Make manual tagging inline instead of from pop-up modal. The goal is for tag mode to let users tag extremely quickly and fluidly. Review PRFAQ.md for additional context.

Acceptance criteria:
- As user types, tags are suggested in the autocomplete display. For example, if a user types "g", it might display something like "groceries" or "gas" if the user has existing tags for those.
- There should be no pop-up modals, everything should be fluid within the same tag mode view. 
- instead of typing "t" for manual tagging, let's make the shortcut "0", this is more similar to the 1-5 quick tagging options.
- If this requires an architectural or in-depth change or a DB schema change or view addition, make sure to notify the user and come up with a proposal instead of implementing. The proposal can live in docs/internal/proposals/todo.