# Task 05: Migrate SimpleFin and Login

## Priority
**MEDIUM** - Setup/configuration commands

## Objective
Migrate `/simplefin` and `/login` to standard CLI. These can be interactive (prompts OK).

## Part A: `treeline login`

### Implementation
```python
@app.command(name="login")
def login_command(
    email: str = typer.Option(None, "--email", help="Email address"),
    password: str = typer.Option(None, "--password", help="Password (not recommended)")
) -> None:
    """Authenticate with Supabase."""
    container = get_container()
    auth_service = container.auth_service()

    # Interactive prompts if not provided
    if not email:
        email = Prompt.ask("Email")

    if not password:
        password = Prompt.ask("Password", password=True)

    result = asyncio.run(auth_service.sign_in(email, password))

    if result.success:
        console.print("[green]✓ Login successful[/green]")
    else:
        display_error(result.error)
        raise typer.Exit(1)
```

### Testing
- `treeline login`
- `treeline login --email user@example.com`

## Part B: `treeline setup simplefin`

Rename `/simplefin` to be more discoverable:

```python
@app.command(name="setup")
def setup_command() -> None:
    """Set up integrations (interactive wizard)."""
    console.print("[bold]Integration Setup[/bold]\n")
    console.print("1. SimpleFIN")
    console.print("2. Cancel")

    choice = Prompt.ask("Select integration", choices=["1", "2"])

    if choice == "1":
        setup_simplefin()

def setup_simplefin() -> None:
    """SimpleFIN setup wizard."""
    user_id = get_authenticated_user_id()

    console.print("\n[bold]SimpleFIN Setup[/bold]")
    console.print("Get your setup token from: https://bridge.simplefin.org/simplefin/create")

    setup_token = Prompt.ask("Setup token")

    container = get_container()
    integration_service = container.integration_service()
    result = asyncio.run(
        integration_service.create_integration(user_id, "simplefin", {"setup_token": setup_token})
    )

    if result.success:
        console.print("[green]✓ SimpleFIN configured successfully[/green]")
    else:
        display_error(result.error)
        raise typer.Exit(1)
```

### Testing
- `treeline login`
- `treeline setup` (interactive)

## Success Criteria
- [ ] `treeline login` handles authentication
- [ ] `treeline setup` provides clear integration wizard
- [ ] Prompts are user-friendly
- [ ] Errors are clear
- [ ] Works without flags (interactive)

## Files to Modify
- `src/treeline/cli.py` - Add commands
- `src/treeline/commands/simplefin.py` - Extract helpers if needed

## Files to Mark for Deletion (later)
- Old `/login` and `/simplefin` handlers (task 10)
