Currently, all CLI commands are bundled in the cli.py file. Instead, we should refactor this to split out all commands into their own file. The new file structure should look like this:
```
src/treeline/
    cli.py # only wiring the commands to the correct command file
    commands/
        status.py
        query.py
        sync.py
        slash/
            status.py
            query.py
            sync.py
            import.py
            etc...
```
It does not have to be exactly like this, but hopefully this provides good enough guidance for you to consider ^.

Acceptance criteria:
- CLI commands and slash commands are split into their own files to make code cleaner and more modular
- All existing tests should pass
- Consider adding new unit tests if necessary