# Local Development Setup

## Prerequisites
- Python 3.12+
- `uv` package manager
- Node.js (for Supabase CLI)

## Environment Setup

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Start local Supabase (for testing):**
   ```bash
   npx supabase start
   ```

   This will output something like:
   ```
   API URL: http://127.0.0.1:54321
   anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Update `.env` file with local Supabase credentials:**
   ```bash
   SUPABASE_URL=http://127.0.0.1:54321
   SUPABASE_KEY=<paste-anon-key-from-supabase-output>
   ```

## Running the CLI

```bash
# Install dependencies
uv sync

# Run the CLI
uv run treeline
```

## Testing Authentication

1. Start the CLI: `uv run treeline`
2. Use `/login` command
3. Choose to create a new account
4. Enter email and password
5. Credentials will be stored in system keyring

## Running Tests

```bash
# Run all unit tests
uv run pytest tests/unit/

# Run specific test file
uv run pytest tests/unit/cli/test_cli_basics.py -v

# Run with coverage
uv run pytest tests/unit/ --cov=treeline --cov-report=term-missing
```

## Stopping Local Supabase

```bash
npx supabase stop
```

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY environment variables must be set"
- Ensure `.env` file exists in project root
- Check that environment variables are set correctly
- Restart the CLI after updating `.env`

### Keyring errors on macOS
- The CLI uses macOS Keychain for credential storage
- Grant access when prompted
- To clear stored credentials: Open Keychain Access app and search for "treeline"
