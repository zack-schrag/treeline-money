# Code Style
- Use ruff for code formatting, and automatic formatting on file save
- ALWAYS use Python type hints

# Implementation Guidelines
- ALWAYS use Test Driven Development unless explicitly told otherwise. All new features should begin with **simple** unit tests that verify the logic and are **failing**. Only then should you begin implementation.
- ALWAYS follow Hexagonal architecture principles. All business logic should be completely independent of underlying technology choices. For example, there should NEVER be code written in the service layer that has specific knowledge of DuckDB or Supabase or OpenAI. ALWAYS review [architecture.md](./docs/internal/architecture.md) for more details about Hexagonal.

# Testing Instructions
## Unit Tests
These have mocked dependencies and verify core logic. For example, a unit test to verify transaction deduplication works during synchronization, with data provider mocked.

Run unit tests: `uv run pytest tests/unit`

## Smoke Tests
These are end-to-end tests intended to test the same functionality a user will itneract with. These should be very basic and not duplicate unit tests, but rather test high-level commands and flows.

Run smoke tests: `uv run pytest tests/smoke`