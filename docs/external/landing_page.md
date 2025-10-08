# Treeline - The IDE for Your Personal Finances

Stop fighting with rigid budgeting apps. Stop manually updating spreadsheets.

**Treeline is the terminal-native financial analysis tool built for developers and power users.**

```
> treeline

🌲 Treeline

> What was my spending on dining last month?

┌─ Query Results ────────────────────────────┐
│ Dining spending for October 2025: $847.32 │
│                                            │
│ SQL used:                                  │
│ SELECT SUM(amount) FROM transactions      │
│ WHERE 'dining' = ANY(tags)                │
│   AND transaction_date >= '2025-10-01'    │
│   AND transaction_date < '2025-11-01'     │
└────────────────────────────────────────────┘

> /chart

📊 Weekly dining trend for last 6 months
[Beautiful terminal chart displayed here]
```

## Why Treeline?

**AI-Powered Insights**
Ask questions in plain English. Get instant answers with SQL you can verify and iterate on.

**Your Data, Your Way**
Direct DuckDB access. Build custom dashboards. Export to Jupyter. Version control your analysis.

**Terminal-Native**
Keyboard-driven workflow. No context switching. Fast, focused, distraction-free.

**Truly Extensible**
Plugin marketplace for budgets, retirement planning, and custom workflows. Or build your own.

## Core Features

### 🤖 AI Chat
Ask questions naturally:
- "What were my top spending categories last month?"
- "Why was September more expensive than August?"
- "Show me my net worth trend over the last year"

The AI shows its work - every answer includes the SQL used. Learn, verify, and iterate.

### 📊 Chart Visualizations
Build terminal charts from any query. Save configurations. Create a dashboard that updates automatically.

Charts powered by PyPlot - beautiful Unicode visualizations optimized for terminal display.

### 🏷️ Smart Tagging
Tag transactions with AI assistance. Tag one transaction, and similar ones get suggested automatically.

**Tagging Power Mode** - Keyboard-driven rapid tagging. Process hundreds of transactions in minutes, not hours.

### 🔍 SQL Analysis Mode
Multi-line SQL editor with:
- Syntax highlighting
- Schema autocomplete
- Query history
- Saved queries and templates
- Chart wizard for instant visualizations

All results displayed as formatted tables in your terminal.

### 🔌 Plugin Ecosystem
Extend Treeline with plugins from the community:

**Simple Budget** - Traditional category-based budgeting built on Treeline's flexible tag system

**Retirement Planner** - Model scenarios and projections based on your actual financial data

**Alert System** - Get notified based on custom query thresholds (low balance, spending spikes, etc.)

Or build your own with:
- Custom schema extensions
- Lifecycle hooks
- New slash commands
- Pre-built queries and dashboards

### 🔐 Privacy First
Your data lives on your computer, encrypted at rest and in transit. Direct file access means you can:
- Back up your data anywhere
- Use git for version control
- Script and automate with standard Unix tools
- Export to any format

**Even Treeline servers can't read your data.** End-to-end encryption means only you have the keys.

## Local-First Philosophy

Treeline feels more like a coding IDE than a traditional finance app:

```
~/.treeline/
├── treeline.db          # Your encrypted DuckDB database
├── queries/             # Saved SQL queries
│   ├── monthly_summary.sql
│   └── spending_trends.sql
├── charts/              # Chart configurations
│   ├── net_worth.tl
│   └── category_breakdown.tl
├── plugins/             # Installed plugins
└── config.toml          # Your preferences
```

Edit a saved query? Just open the file. Version control your financial analysis? `git init`. Build custom automation? Write a bash script.

**Your data is actually yours.**

## Who Is This For?

Treeline is built for technical users who want:

✅ **Data analysts** - SQL access, custom metrics, Jupyter integration
✅ **Software engineers** - Scriptable, automatable, version-controllable
✅ **Quant folks** - Direct data access for custom models and analysis
✅ **Privacy-conscious users** - Local-first, encrypted, exportable
✅ **Power users** - Frustrated with rigid budgeting apps and manual spreadsheets

## How It Works

**1. Connect Your Accounts**
- SimpleFIN (recommended) - automatic sync with 12,000+ institutions
- Plaid - broader support (paid tier)
- Manual CSV imports - works with any bank

**2. Organize Your Data**
- AI-assisted tagging for categorization
- Multi-tag support (tag "vacation dining" with both `vacation` and `dining`)
- Automatic matching for recurring transactions

**3. Ask Questions**
- Natural language queries powered by AI
- Direct SQL for precision and control
- Build and save custom analyses

**4. Visualize & Share**
- Create charts from any query
- Configure terminal dashboard
- Export reports as markdown
- View on mobile app (read-only)

**5. Automate & Extend**
- Install community plugins
- Set up alerts and monitoring
- Build custom automation scripts
- Integrate with your existing workflows

## Pricing

**Free Tier**
- Core features (sync, tagging, SQL queries, charts)
- SimpleFIN sync only
- No AI assistance
- Local storage only

**Pro - $X/month**
- N AI credits per month
- Plaid integration option
- Cloud backups (encrypted)
- Mobile app access
- Plugin marketplace access

**Power - $XX/month**
- XX AI credits per month
- Priority support
- Advanced plugins
- Shared access (spouse/partner)

**Unlimited - $XXX/month**
- Unlimited AI queries
- White-glove onboarding
- Custom plugin development
- API access

## Getting Started

```bash
# Install Treeline
brew install treeline

# Initialize
treeline init

# Connect your bank
treeline /simplefin

# Start exploring
treeline

> What's my net worth?
> /tag
> /chart
```

## Testimonials

> "I've spent years trying every budgeting app and building custom spreadsheets. Treeline is the first tool that actually lets me ask the questions I want. As a data analyst, working in SQL feels natural - and the AI helps when I need it."
>
> — **Albert, Data Analyst, San Francisco**

> "The tagging power mode is insane. Every app makes categorization a chore. With Treeline, I can process weeks of transactions in minutes. The suggested tags just get better as I use it."
>
> — **Blake, Software Engineer, New York**

> "AI tools have gotten so good, and having one purpose-built for my finances is amazing. I can ask 'show me my net worth trend' and instantly get a chart in my terminal. And I can check the SQL it used!"
>
> — **Charlie, Founder, Seattle**

> "Most fun I've had analyzing finances. I've customized it exactly to my life - custom alerts, automated tagging, shared reports with my husband. The mobile app gives him a simple view of the dashboards I've built."
>
> — **Delila, Engineering Manager, Chicago**

## FAQ

**Do I need to know SQL?**
Not necessarily - the AI chat works great for most questions. But SQL gives you precision and power when you need it. The AI shows you the SQL it uses, so you can learn as you go.

**Why terminal/CLI?**
Personal finance analysis is iterative and dynamic - like coding. What works in 2025 might not work in 2027. We give you direct access to your data and get out of your way. Plus, terminal workflows are fast, keyboard-driven, and distraction-free.

**Can I use this for budgeting?**
Yes! Install the Simple Budget plugin from the marketplace. We believe tags are more flexible than rigid categories, but the plugin gives you traditional budgeting if you want it.

**How secure is my data?**
Your data lives on your machine, encrypted at rest and in transit. Cloud backups are end-to-end encrypted - even Treeline servers can't read your data. You can also export everything and keep it locally if you prefer.

**Is there a mobile app?**
Yes! The mobile app provides read-only access to your dashboards, charts, and AI assistant. Perfect for checking your finances on the go or sharing with a partner who doesn't use the CLI.

**Can I export my data?**
Absolutely. Your data lives in a DuckDB file you can access directly. Export to CSV, Parquet, JSON, or connect from Jupyter/Python. Use DBeaver or any SQL tool. It's your data.

**Can I automate things?**
Yes! Run Treeline commands in scripts. Build custom automation. Some users have built:
- Monthly expense reports emailed automatically
- Text alerts for specific transaction patterns
- Custom sync schedules
- Integration with home automation

**What about collaborative features?**
Pro tier includes shared access (great for couples). The mobile app lets non-technical users view your dashboards. For teams, contact us about custom solutions.

## Vision

We're building the most powerful personal finance tool for technical users. A tool that:

- Respects your intelligence (shows its work, gives you access)
- Respects your privacy (local-first, encrypted, exportable)
- Respects your workflow (terminal-native, scriptable, extensible)
- Grows with you (plugins, custom analysis, automation)

**Your financial data is too important to be locked in someone else's app.**

---

Ready to take control of your financial data?

```bash
brew install treeline
treeline init
```

---

*Note: Treeline is currently in private beta. Join the waitlist at treeline.money*

## Terminal Landing Page Concept

*Future idea: Interactive terminal-style landing page where visitors can type commands:*

```
$ /about     # Learn more about Treeline
$ /pricing   # View pricing tiers
$ /demo      # See interactive demo
$ /waitlist  # Join the beta
$ help       # Show available commands
```

*Would provide an immersive, on-brand experience that demonstrates the product while educating visitors.*
