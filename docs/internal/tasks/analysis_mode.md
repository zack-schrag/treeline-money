NOT READY TO COMPLETE YET - DO NOT IMPLEMENT
---

Currently, a user's ability to analyze their data in the TUI is fairly limited. They have 2 options currently:
1. AI chat mode and explicitly ask the agent to run some analysis and maybe display a chart
2. /query, which only accepts a single line, inline query

For quick things, these are fine. But for actual analysis, we need users to have the ability to go deeper. Some examples of things users may encounter:
- A user starts with an AI chat and asks it to display a net worth chart for the last 3 months. Then, they may want to edit the SQL the AI used, rather than asking the AI. Then they may want to create a different chart based on the output. 
- A user may want to do some kind of analysis and then export the findings. Perhaps they'd want to export as a simple markdown file, complete with the charts display (this should work since it's terminal output, right?) and text descriptions, etc.
- A user may want to save queries for future use, as well as a chart configuration for it. For example, maybe they want a saved query / chart that displays their weekly spending on "eating out" tag over the last 6 weeks. Maybe they could view this by doing something like "/chart my_weekly_spending.tl" which displays the chart based on the treeline (".tl" file) config file for that chart / query.
- A user may want to directly write multi-line sql themselves, with autocomplete features (e.g., suggest table names and columns as the user is typing), and then view the results as a regular table (same as /query currently, but allow multi-line and autocomplete, syntax highlighting, etc.)

Overall, the challenge here is how to build an intuitive, smooth, and fast UX for a terminal based analysis tool. 

Acceptance criteria:
- Design proposal is created in docs/internal/proposals
- New task is created in docs/internal/tasks outlining specific work. Follow the same file pattern as in other task files (e.g. Acceptance criteria).