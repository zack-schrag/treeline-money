# Principles
## Local-first
The app is local-first, meaning all major operations occur on the user's machine, not on the server. The server is used minimally - primarily for authentication and database backups.

## AI native
The app is AI native, meaning AI is a first-class citizen in the experience. Treeline is inspired heavily by tools such as Claude Code.

## Hexagonal architecture
Hexagonal architecture is how code is structured in this project. Domain classes should be self-contained, and abstraction design is paramount to maintaining the integrity of the codebase. For example:
```
# BAD abstraction
class DataProvider(ABC):
    def get_simplefin_transactions(start_date, end_date, simplefin_access_url):
        pass
```
```
# GOOD abstraction
class DataProvider(ABC):
    def get_transactions(start_date: str, end_date: str, provider_options: Dict[str, Any]):
        pass
```
Note the difference between these examples. The first "leaks" the details of the underlying technology choice (SimpleFIN). This makes it harder to add support for other providers such as Plaid, CSV imports, etc. The second example keeps the technology choices separated out from the abstraction. This good abstraction can now be used for any new tech choice, without changing the method signature(s).

# Vibes
This section describes what the app should *feel* like to the user. Note this does not describe specific implementation details, but rather overall *feel* of the app and attempting to describe the intangibles a user should experience while using Treeline.

- It should feel more like coding than a traditional UI based personal finance app. The target audience is tech-savvy people who are comfortable in the terminal and with SQL. We want to let users feel the raw power of 1) having direct access to their data and 2) the AI agent.
- It should feel *fun*. The target audience are the types of people who have fun building spreadsheets, automations, and generally like tinkering. Using Treeline should feel fun for these people, not a chore. 
- It should feel *obvious*. Anytime we're building a new feature, ask "what would be the most obvious way for a user to interact with this?".

# Tech Stack
## CLI
- Python (version 3.13)
  - Typer: https://typer.tiangolo.com/#typer-slim
  - Rich: https://rich.readthedocs.io/en/latest/
  - Textual: https://github.com/Textualize/textual
- DuckDB: (version 1.4 or above)
- YouPlot: https://duckdb.org/docs/stable/guides/data_viewers/youplot.html

## Server Side
- Supabase -> authentication and DuckDB backups

# Directory Structure
```
src/treeline/
    cli.py # Typer CLI entry point
    abstractions/ # all "ports" should be defined in here
        auth.py 
        db.py # DB abstraction for executing queries
        backup.py # Abstraction for managing DB backups and restore
        ai.py # AI abstraction for interacting with LLM APIs
        data.py # DataProvider abstraction
    app/ # Core business logic that is independent of underlying technology choices (e.g. transaction fetching and deduplication)
        service.py 
    infra/ # this is where "adapter" implementations live, one file per underlying technology or api.
        duckdb.py
        simplefin.py
        openai.py
        anthropic.py
        supabase.py
    domain/
        domain.py # contains domain classes such as Account, Transaction, etc.
    
```