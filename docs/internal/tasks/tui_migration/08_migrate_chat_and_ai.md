# Task 08: Migrate Chat and AI Commands

## Priority
**HIGH** - Important for AI-native experience

## Objective
Migrate AI chat functionality to `treeline chat` and add `treeline ask` for one-shot queries.

## Part A: `treeline chat`

### Implementation
```python
@app.command(name="chat")
def chat_command() -> None:
    """Start an interactive AI conversation about your finances."""
    user_id = get_authenticated_user_id()

    console.print("[bold]AI Chat Mode[/bold]")
    console.print("Ask questions about your finances. Type 'exit' to quit.\n")

    container = get_container()
    agent_service = container.agent_service()

    # Interactive loop (similar to old REPL but AI-focused)
    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]")

            if user_input.lower() in ("exit", "quit"):
                break

            # Show thinking indicator
            with console.status("[dim]Thinking...[/dim]"):
                result = asyncio.run(
                    agent_service.process_message(user_id, user_input)
                )

            if result.success:
                console.print(f"[bold green]AI[/bold green]: {result.data['response']}\n")
            else:
                display_error(result.error)

        except KeyboardInterrupt:
            break

    console.print("\n[dim]Chat ended[/dim]")
```

### Testing
- `treeline chat`
- Ask various questions
- Verify conversation context maintained
- Test exit flows

## Part B: `treeline ask`

### Implementation
```python
@app.command(name="ask")
def ask_command(
    question: str = typer.Argument(..., help="Question to ask AI"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Ask AI a one-shot question about your finances."""
    user_id = get_authenticated_user_id()

    container = get_container()
    agent_service = container.agent_service()

    result = asyncio.run(
        agent_service.process_message(user_id, question)
    )

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    if json_output:
        output_json(result.data)
    else:
        console.print(result.data['response'])
```

### Testing
- `treeline ask "what's my current balance?"`
- `treeline ask "show spending by category" --json`

## Part C: Clear Command

```python
@app.command(name="clear")
def clear_command() -> None:
    """Clear AI conversation history."""
    user_id = get_authenticated_user_id()

    container = get_container()
    agent_service = container.agent_service()
    result = asyncio.run(agent_service.clear_session(user_id))

    if result.success:
        console.print("[green]✓ Conversation cleared[/green]")
```

## Success Criteria
- [ ] `treeline chat` provides interactive AI conversation
- [ ] `treeline ask` handles one-shot queries
- [ ] Conversation context maintained in chat mode
- [ ] `treeline clear` clears history
- [ ] Both support --json for scripting

## Files to Modify
- `src/treeline/cli.py` - Add commands
- `src/treeline/app/service.py` - Verify AgentService

## Files to Mark for Deletion (later)
- Old natural language handler in REPL (task 10)
- `commands/chat.py` if exists
