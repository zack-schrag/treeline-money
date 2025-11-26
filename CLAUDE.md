# Project Structure

This is a monorepo with three main components:

- **core/** - Rust library with shared business logic (future: PyO3 bindings for CLI)
- **cli/** - Python CLI application (Typer)
- **ui/** - Tauri desktop application (Rust + Svelte)

# Code Style

## Python (cli/)
- Use ruff for code formatting: `uvx ruff format cli/`
- ALWAYS use Python type hints

## Rust (core/, ui/src-tauri/)
- Use `cargo fmt` for formatting
- Use `cargo clippy` for linting

# Implementation Guidelines
- ALWAYS use Test Driven Development unless explicitly told otherwise
- ALWAYS follow Hexagonal architecture principles
- ALWAYS run unit tests before doing a git commit, unless explicitly asked not to

# CLI Architecture Rules
- The CLI (`cli/src/treeline/cli.py`) MUST be a thin presentation layer
- The CLI MUST ONLY interact with services from `cli/src/treeline/app/service.py`
- The CLI MUST NEVER directly call repositories, providers, or any other abstractions
- All business logic MUST live in the service layer, NOT in the CLI
- ALL domain models MUST be defined in `cli/src/treeline/domain.py`

# Testing Instructions

## Python Unit Tests
Run from the cli/ directory:
```bash
cd cli && uv run pytest tests/unit
```

## Rust Tests
```bash
cargo test -p treeline-core
```

# Running the CLI
```bash
cd cli && uv run tl --help
```

# Running the UI (Tauri)
```bash
cd ui && npm run tauri:dev
```
