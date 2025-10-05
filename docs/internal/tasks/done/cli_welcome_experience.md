Currently, the UX for entering the REPL is underwhelming:
```
schrag@Zacks-MacBook-Air treeline-money-v2 % uv run treeline

🌲 Welcome to Treeline!

Logged in as test@treeline.dev

Type /help to see available commands
Type exit or press Ctrl+C to quit

>: 
```
Contrast this with Claude Code, which has fun visuals and useful information:
```

╭─── Claude Code v2.0.8 ──────────────────────────────────────────────╮
│                                          │ Recent activity          │
│            Welcome back Zack!            │ 36m ago  Review this pr… │
│                                          │ 2h ago   This session i… │
│                                          │ 2h ago   This session i… │
│                  ▐▛███▜▌                 │ /resume for more         │
│                 ▝▜█████▛▘                │ ──────────────────────── │
│                   ▘▘ ▝▝                  │ What's new               │
│                                          │ Update Bedrock default … │
│                                          │ IDE: Add drag-and-drop … │
│         Sonnet 4.5 · Claude Max          │ /context: Fix counting … │
│   /Users/schrag/code/treeline-money-v2   │ /release-notes for more  │
╰─────────────────────────────────────────────────────────────────────╯

─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
> Try "how does anthropic_adapter.py work?"
─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
```
Acceptance criteria:
- The Treeline CLI welcome UX is visually appealling and *fun*. Some ideas: a pixelated mountain with snow on the top and a distinct tree-line in it.
- The welcome UX should display *useful* information. Some ideas: recently used queries from "/query" slash command, last successful /sync. Don't do anything that requires complex changes, but if it's easy to get the information for it, consider adding to the welcome UX information screen.
