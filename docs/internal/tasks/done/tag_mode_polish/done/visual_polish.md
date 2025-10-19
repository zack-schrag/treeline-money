This task is just about polishing some of the visual aspects of tag mode.

Acceptance criteria:
- Instead of "Clear" for the "c" command, explicity say something more like "Clear Tags for transaction". It may not fit neatly, so consider the best wording.
- At the top, there is a "Total", which really is the total transactions on the current page. Instead, this should be more clear it's not the total transactions in the DB, just the current page. 
- The "u" command just says "Filter", but a user won't know what that means. Be more explicit, something like "Toggle untagged / tagged". Again, consider the best wording here.
- The n/p shortcuts feel a little unnatural? Consider normal key navigation shortcuts for next and previous in other popular terminal apps
- Negative amounts are highlighted red, postive green
- The tags columns has a more visually appealling look for tags. If this were a real UI, I'd use a pill or badge component to make it look nice. For TUI, consider a nice visually appealling way to display tags (there can be multiple for any given transaction)
