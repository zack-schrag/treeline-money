# Project Structure

This is a monorepo with two main components:

- **cli/** - Python CLI application (Typer)
- **ui/** - Tauri desktop application (Rust + Svelte)

# Code Style

## Python (cli/)
- Use ruff for code formatting: `uvx ruff format cli/`
- ALWAYS use Python type hints

## Rust (ui/src-tauri/)
- Use `cargo fmt` for formatting
- Use `cargo clippy` for linting

# CLI Implementation Guidelines
- ALWAYS follow Hexagonal architecture principles
- Run tests before doing a git commit, unless explicitly asked not to

# CLI Architecture Rules
- The CLI (`cli/src/treeline/cli.py`) MUST be a thin presentation layer
- The CLI MUST ONLY interact with services from `cli/src/treeline/app/service.py`
- The CLI MUST NEVER directly call repositories, providers, or any other abstractions
- All business logic MUST live in the service layer, NOT in the CLI
- ALL domain models MUST be defined in `cli/src/treeline/domain.py`

# Testing Instructions

## Testing Philosophy
- **Prefer smoke tests over unit tests** for CLI commands
- Smoke tests run actual CLI commands via subprocess in demo mode - see `tests/smoke/`
- Unit tests are good for edge cases that are hard to hit via CLI (e.g., malformed CSV formats, unusual date parsing)
- Simple smoke tests are preferred over complex unit tests that require maintenance

## Running Tests
```bash
# Smoke tests (preferred for CLI features)
cd cli && uv run pytest tests/smoke -v

# Unit tests (for edge cases and complex parsing logic)
cd cli && uv run pytest tests/unit -v

# All tests
cd cli && uv run pytest tests/ -v
```

# Running the CLI
```bash
cd cli && uv run tl --help
```

# Running the UI (Tauri)
```bash
cd ui && npm run tauri:dev
```
