# Quickstart
Welcome to Treeline! Follow this guide to get setup with Treeline, import your data, and start asking questions of your data!

# Step 1: Installation
## pip Install
```
pip install treeline-money
```

## Native Install (coming soon)

# Step 2: Log in or create an account
Treeline requires an account to use, you'll be prompted to login when you start the session:
```
treeline
```
```
/login
# Follow the prompts to log in or create your account
```

# Step 3: Start a session
First 
```
cd /path/to/data
treeline
# Initializes treeline in the current directory
# This creates a folder "treeline" in /path/to/data
```

You'll see the welcome prompt:
```
TODO

* Weclome to Treeline! 🌲

...
```

# Step 4: Import your data
Treeline supports a few ways to get your data:
- SimpleFIN (recommended)
- Plaid (coming soon)
- CSV import (coming soon)

## SimpleFIN (recommended)
SimpleFIN let's you securely share your financial data with apps (like Treeline!). We are not associated with SimpleFIN, it's a completely a separate entity, and you will need to have your own paid account with them. It only costs $1.50 per month, or $15 a year (we offset the costs of this in your Treeline paid account if you use SimpleFIN). This is our recommended approach for a few reasons:
1. It's extremely simple to get started. Sign up for an account, connect your bank accounts, and generate a setup token. Boom.
2. You can reuse your bank accounts for a different app, if you choose.  
    One of the core value of Treeline is that your data is actually *your* data, and you should be able to take it with you with little to no friction. SimpleFIN allows you to separate your bank account connections from a specific app (even Treeline!). If you find Treeline isn't a good fit for you, you can choose a different app that supports SimpleFIN, without having to renter your account credentials again and giving your data to yet another app.

3. It's the cheapest for us to support (full transparency!), compared to alternatives like Plaid. 

> Note: because using SimpleFIN also helps us, we provide a one-time $NNN credit to your account and a recurring $1.50 a month credit, as a thank you for helping us keep our costs down.

### Setup
If you don't already have a SimpleFIN account, go to https://beta-bridge.simplefin.org/ and create an account, then follow the steps:
1. Generate a setup token, using the instructions here: https://beta-bridge.simplefin.org/info/developers
2. In your Treeline CLI session, use the command `/simplefin`, you'll receive a prompt that looks like this:
```
> /simplefin
    Note: if you don't have a SimpleFIN account, create one here: https://beta-bridge.simplefin.org/

    Enter your SimpleFIN setup token: ****
    Enter how many days of transactions to import (max 90 days ago): 90
```
3. You will be shown a preview of the transactions, and can confirm if everything looks good.

You're all set! Treeline will automatically fetch your latest account data for you daily.

## Plaid (coming soon)
Plaid is one of the most common ways to connect your bank accounts to apps. 

## CSV Import (coming soon)
You can import CSV files downloaded from your bank. 

# Step 5: Ask questions about your data
At this point, you're setup and ready to go. Start asking questions about your data:
```
> What are my top 3 most expensive transactions last week?
```
```
> Show me my net worth trend over the last 90 days
```

# Step 6: Try tagging power-mode (name TBD)
Start tagging power-mode with the slash command:
```
> /tag
```
This will show all transactions for you to quickly key through and apply suggested tags or custom tags.

# Essential Commands

Command | Description | Example
--- | --- | --- 
treeline | Enter interactive mode | `treeline`
/help | Show available commands | `> /help`
/login | Login or create your Treeline account | `> /login`
/status | Shows summary of current state of your financial data | `> /status`
/simplefin | Setup SimpleFIN connection | `> /simplefin`
/import | Import CSV file of transactions | `> /import`
/tag | Enter tagging power mode | `> /tag`

# What's Next?
TODO