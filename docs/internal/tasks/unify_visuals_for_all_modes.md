Currently, we have a few slash commands that enter into a special TUI view:
- /tag
- /analysis

The UX is close, but not consistent across both. One uses Rich, the other exclusively prompt_toolkit (out of necessity). /tag displays keyboard shortcuts subtly at the top as a subheader, /analysis displays at the very top in a highlighted menu. There are many sublte differences like this. Your goal: created a unified component styling for TUI modes like this. It should have a consistent look and feel. And for future TUI modes, it should also adopt this pattern.

Acceptance criteria:
- All existing TUI modes have a consistent look and feel. Confirmed explicitly by the user
- All existing TUI modes share common components