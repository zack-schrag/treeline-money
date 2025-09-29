# MVP
## Phase 1: Basic Slash Commands
- `/login`
  - [ ] Build minimal authentication browser page with Supabase. Email / password only for now.
  - [ ] On success, return to the terminal and store credentials in OS abstracted way. For macOS, use keyring.
- `/status`
  - [ ] Display a few basic things about user's data: top 5 spending tags, net worth chart, etc.
- `/simplefin`
  - [ ] Input setup token, and store integration details locally in DuckDB "integrations" table.
  - [ ] Display preview on successful access token exchange.

## Phase 2: AI integration
This phase will be a more in-depth AI agent implementation. Of course, we need to abstract the LLM API, however, I think we'll need more than *only* that. Some possible things (to be fleshed out after phase 1 is complete):
- [ ] System prompt with details about DuckDB schema
- [ ] System prompt details about YouPlot and how to plot in the terminal
- [ ] MCP tools we might need to build: Youplot, DuckDB
- [ ] Context management for deep analysis sessions. Need to consider how to approach this - if at all.

# Future Enhancements
- [ ] Periodic DuckDB backups to Supabase storage

# Ideas
TODO