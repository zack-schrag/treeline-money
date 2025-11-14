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
    def get_simplefin_transactions(self, start_date, end_date, simplefin_access_url):
        pass
```
```
# GOOD abstraction
class DataProvider(ABC):
    def get_transactions(self, start_date: str, end_date: str, provider_options: Dict[str, Any]):
        pass
```
Note the difference between these examples. The first "leaks" the details of the underlying technology choice (SimpleFIN). This makes it harder to add support for other providers such as Plaid, CSV imports, etc. The second example keeps the technology choices separated out from the abstraction. This good abstraction can now be used for any new tech choice, without changing the method signature(s).

Another example of the boundary between the CLI layer and the service layer:
```
# BAD
def some_cli_command_handler():
    service = SyncService()

    transactions = service.sync_transactions()

    # BAD: this is business logic and should belong in the sync logic!
    transactions = remove_duplicates(transactions)

    # display results...

# GOOD
def some_cli_command_handler():
    service = SyncService()

    # GOOD: deduplication logic lives in sync_transactions, not in CLI layer
    transactions = service.sync_transactions()

    # display results...
```
The first example has business logic in the CLI command handler, which violates the architecture. Instead, this core business logic should belong in the service itself. The CLI's responsibility is to translate user input to service calls, and translate service output into display formatting in the terminal. 

### Critical Architecture Rules
**Domain Models:**
- ALL domain models MUST be defined in `src/treeline/domain.py`
- Domain models should NEVER be defined in commands, CLI, or infrastructure layers
- If you're creating a new entity (Account, Transaction, etc.), it goes in `domain.py`

**Layer Responsibilities:**
- **CLI/Commands**: Parse input, call services, display results. No business logic, no file I/O, no database access.
- **Services**: Business logic only. Use abstractions for all external concerns.
- **Abstractions**: Define interfaces (ABCs). No implementation details.
- **Infrastructure**: Implement abstractions. All technology-specific code lives here.

# Directory Structure
```
src/treeline/
    cli.py # Typer CLI entry point w/ all commands
    domain.py # contains domain classes such as Account, Transaction, etc.
    abstractions/ # all "ports" should be defined in here
    app/ # Core business logic that is independent of underlying technology choices (e.g. transaction fetching and deduplication)
        service.py # core business logic classes
        container.py # DI container for resolving deps
    infra/ # this is where "adapter" implementations live, one file per underlying technology or api.
```

# Database Schema
See src/treeline/infra/migrations for up-to-date schema definition.
