NOT READY TO COMPLETE YET - DO NOT IMPLEMENT
---

Currently, a user's ability to analyze their data in the TUI is fairly limited. They have 2 options currently:
1. AI chat mode and explicitly ask the agent to run some analysis and maybe display a chart
2. /query, which only accepts a single line, inline query



the only way to display a chart is through the AI chat prompt, where it will use the chart pyplot MCP tools to determine displaying a chart based on the SQL query.

In addition to this, we want to allow a user to build a chart themselves from a sql query. The tricky part here is that this is a terminal UI as opposed to a normal charts app where you can click around. So thinking through a sleek, smooth, and intuitive interface to allow a user to write queries and build charts from it will require ultrathinking.

I think some common users flows that we should consider:
- a user starts with an AI chat, but then wants to edit the provided SQL

Acceptance criteria:
- Design proposal is created in docs/internal/proposals
- New task is created in docs/internal/tasks outlining specific work. Follow the same file pattern as in other task files (e.g. Acceptance criteria).