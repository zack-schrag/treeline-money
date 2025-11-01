# Code Style
- Use ruff for code formatting, and run `uvx ruff format` after file modifications
- ALWAYS use Python type hints

# Implementation Guidelines
- ALWAYS use Test Driven Development unless explicitly told otherwise. All new features should begin with **simple** unit tests that verify the logic and are **failing**. Only then should you begin implementation.
- ALWAYS follow Hexagonal architecture principles. All business logic should be completely independent of underlying technology choices. For example, there should NEVER be code written in the service layer that has specific knowledge of DuckDB or Supabase. ALWAYS review [architecture.md](./docs/internal/architecture.md) for more details about Hexagonal.
- ALWAYS run unit tests (see below) before doing a git commit, unless explicity asked not to.

# CLI Architecture Rules
- The CLI (`src/treeline/cli.py`) MUST be a thin presentation layer
- The CLI MUST ONLY interact with services from `src/treeline/app/service.py`
- The CLI MUST NEVER directly call repositories, providers, or any other abstractions
- The CLI MUST NEVER perform direct file I/O operations (use storage abstractions via container)
- All business logic MUST live in the service layer, NOT in the CLI
- The CLI should only:
  1. Parse user input
  2. Call the appropriate service method
  3. Display the results to the user
- ALL domain models (Account, Transaction, ChartConfig, etc.) MUST be defined in `src/treeline/domain.py`

# Testing Instructions
## Unit Tests
These have mocked dependencies and verify core logic. For example, a unit test to verify transaction deduplication works during synchronization, with data provider mocked.

Run unit tests: `uv run pytest tests/unit`