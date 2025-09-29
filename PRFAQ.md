# Treeline Vision
Treeline is a CLI-first personal financial analysis tool. 

## PRFAQ
Treeline Money LLC, today announced the introduction of Treeline CLI, the most powerful way to manage and analyze personal finances. Previously, power users have been stuck building custom spreadsheets, manually exporting CSV files, or forced to conform to a budget app's prescriptive tools. Treeline syncs and provides direct access to user's own data, bringing an AI-first approach to analyzing and managing financial data. 

Treeline brings a CLI experience inspired by Claude Code and Codex CLI, designed to bring users as close as possible to their data, while providing a thin layer of convenience for things such as natural language queries, chart visualizations, and rapid transaction tagging. Because Treeline provides you direct access to the underlying data in a personal DuckDB file, users are able to perform their own analysis using tools they are already familiar with such as SQL, Jupyter notebooks, Python scripts, etc. Additionally, user's data is encrypted on the user's computer, and backed up to Treeline servers while staying encrypted. I.e., only the end user can view their data, not even Treeline servers or employees can view user's data. 

Treeline is local-first, all data can be viewed and stored in a single folder on a filesystem. In this sense, using Treeline feels much more like a coding IDE than a traditional personal finance app. For example, users can edit a saved query directly by opening the file and editing it.

Treeline brings a rich set of features that let users endlessly customize their own experience:

### AI Chat
Using natural language, users can ask direct questions about their finance data:
- "What were my top 3 tags for spending last week?" -> displays a table with the results.
- "Why was my spending so much higher in September vs August?" -> perform several queries to analyze the difference, and summarizes the results to the user.
- "Show me my weekly spending trend for the last 6 months" -> displays a line chart showing net worth history over the last 6 months.

The AI agent shows its work by always displaying the SQL it used to get to the answers, making it easy for users to tweak and iteratively edit the SQL directly to get exactly the answers they need.

### Chart Visualizations
Users can build chart visualizations in the terminal directly from queries. Under the hood, Treeline pipes DuckDB query results into YouPlot for visualizations. Users are able to save the queries and chart for later usage, and configure their home terminal "dashboard" with charts and tables to display.

### Tagging Power Mode
Tagging power mode lets users rapidly apply tags to transactions with as little friction as possible. Users can jump around between transactions using keyboard shortcuts, and are provided suggested tags based on a combination of ML algorithms and frequently used tags. 

### Custom Alerts
Users can configure to be notified based on the results of queries and specified thresholds. For example, a user may choose to be notified if their account balance is below $N for 3 days in a row. Or if their weekly spending trend has trended upward for 3 months (a slow drift). Treeline provides dozens of alert templates to get started, as well as many more shared by the community.

### Plugin Marketplace
Treeline has a powerful plugin model, allow users to build and publish their own plugins. Some examples:
- Simple Budget: simple budget system allowing you to define your own categories, built on top of Treeline's standard schema.
- Retirement Planner: based on your account data, this plugin helps you plan your retirement through analyzing different scenarios and provides projections.

Plugins can be built using the following components:
- DB schema additions: tables can be added
- Hooks: custom logic to execute at certain lifecycle events (transaction added, account balance updated, alert triggered, etc.)
- Slash commands: plugins can add slash commands
- Queries and charts: pre-built queries and charts ready to be used as soon as the plugin is installed.

## Pricing
Treeline has a simple pricing model:
- Free -> no AI, SimpleFIN only, no backups, no mobile app
- $XXX month -> N credits for AI, option for Plaid instead of SimpleFIN, hourly backups, mobile app access. Access to plugin marketplace.
- $XXX month -> N*X credits for AI, authorized users like spouses
- $XXX month -> unlimited AI queries (subject to abuse guardrails)

## Customer Testimonies
> I have spent years trying every budgeting app and even building my own custom spreadsheets. But they all lacked something: budgeting apps were too rigid. Custom spreadsheets lacked automation. Treeline is the first tool that actually lets me ask the questions I want of my data. As a data analyst, I'm used to working in SQL and Python, so it was a natural fit for me to build my own visualizations and analysis with the tools I'm already familiar with.
> - Albert from San Francisco

> The tagging power mode is INSANE. Every budgeting app has their own cute, but inconvenient way of making you categorize your transactions. If you miss a few days, god forbid a few weeks, you have a big chore on your hands to catch up. Treeline's tagging power mode is the first tool I've used that doesn't make me hate my life when I have a big pile of transactions to tag. And the suggested tags just get better and better as I use it more!
> - Blake from New York

> AI tools have gotten so good recently, I'm stoked to have one purpose-built for my finance data. I can quickly ask it "show me my net worth trend over the last 3 years" and it instantly displays a beautiful chart right in the terminal, and I can even check its work and edit the SQL it used! Really amazing, it feels like I'm finally in the driver's seat of my own data.
> - Charlie from Seattle

> Using Treeline is the most fun I've had analyzing my personal finances in a long time. I can customize it exactly to my life. I have alerts setup for overspending for certain tags, I have custom tagging automation I built using the hooks feature, and I can share reports easily with my husband so he can be aware of the state of our finances too. My husband is not tech savvy, so having the mobile app for him to have a simple read-only view of the charts I've built is really useful.
> - Delila from Chicago 

## External FAQ
1. Do I have to know SQL?  
    Not necessarily, you can get by without it using the AI chat. However, we don't hide it, so you should not be intimidated by it. The AI assistant can help guide you, but like any AI system, it can be wrong. Having some familiarity with SQL is helpful, but not absolutely required.

2. Why CLI?  
    We took heavy inspiration from Claude Code and Codex CLI. Analyzing your personal data is a dynamic and iterative process, much like coding. What might work for you in 2025, might not make sense in 2027. Analysis is often ad-hoc and messy, and doesn't always fit nicely into cookie cutter dashboards and charts. Your analysis might change, but your data won't. We do our best to give you direct access to your data, make it easy to ask questions of your data, and get out of your way.

3. Do you have a mobile app?  
   Yes! The Treeline app provides a read-only view of the things you've created using the CLI. You can view charts, alerts, reports. You can also ask freeform questions to be answered by the AI agent.

4. Can I budget with this?  
   Short answer: yes, with a plugin!
   Long answer: One of the fundamental insights that started Treeline - the data structure for personal financial data does not change, and as long as you have the data, you can do anything you want with it. Our philosophy at Treeline is to provide the most direct access to your foundational financial data. Budgeting is not fundamental to the data itself, but rather one of many ways to use your data. Given this, we don't provide budgeting natively, but do provide a simple budgeting plugin.
   We think categories are restrictive. If you go out to eat on a vacation, should that be categorized as "Eating Out" or "Vacation"? We don't think you should have to pick one, so instead we have a simple concept of "tags". You can tag a transaction with as many tags as you like and that make sense to you. If you want a strict budget with categories, feel free to install the "Simple Budget" plugin built by the community.

5. How secure is my data?  
   We believe your data should actually be *your* data, and you should be able to take it with you where you want to. Your data in Treeline lives on your computer and is fully encrypted using bank-level standards, at transit and at rest.

6. Can I bring my own AI API key?  
    Yes, we support OpenAI, Anthropic, and local ollama, with plans to support more in the future.

7. How do I get my data into Treeline?
    Treeline supports SimpleFIN (recommended), manual CSV imports, and Plaid.

8. Can I build my own scripts and automation?  
    Yes! That's the beauty of a CLI. You can run commands in non-interactive mode to embed them into your own scripts. Some of our users have built their own automations such as:
    - Export a markdown summary of the past month's transactions and highlights.
    - Send a text message anytime a transaction containing the text "Target" is ingested.
