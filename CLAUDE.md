# Code Style
- Use ruff for code formatting, and automatic formatting on file save
- ALWAYS use Python type hints

# Implementation Guidelines
- ALWAYS use Test Driven Development unless explicitly told otherwise. All new features should begin with **simple** unit tests that verify the logic and are **failing**. Only then should you begin implementation.
- ALWAYS follow Hexagonal architecture principles. All business logic should be completely independent of underlying technology choices. For example, there should NEVER be code written in the service layer that has specific knowledge of DuckDB or Supabase or OpenAI. ALWAYS review [architecture.md](./docs/internal/architecture.md) for more details about Hexagonal.

# CLI Architecture Rules
- The CLI (`src/treeline/cli.py`) MUST be a thin presentation layer
- The CLI MUST ONLY interact with services from `src/treeline/app/service.py`
- The CLI MUST NEVER directly call repositories, providers, or any other abstractions
- All business logic MUST live in the service layer, NOT in the CLI
- The CLI should only:
  1. Parse user input
  2. Call the appropriate service method
  3. Display the results to the user

# Testing Instructions
## Unit Tests
These have mocked dependencies and verify core logic. For example, a unit test to verify transaction deduplication works during synchronization, with data provider mocked.

Run unit tests: `uv run pytest tests/unit`

## Smoke Tests
These are end-to-end tests intended to test the same functionality a user will itneract with. These should be very basic and not duplicate unit tests, but rather test high-level commands and flows.

Run smoke tests: `uv run pytest tests/smoke`