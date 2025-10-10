# Power Session Protocol

## Overview
A "power session" is a focused work mode where I continuously implement tasks from `docs/internal/tasks/` until no more tasks remain. Tasks are defined as markdown files in the tasks directory.

## How It Works

### Before Starting
1. Review key project documentation:
   - `CLAUDE.md` - Code style and implementation guidelines
   - `PRFAQ.md` - Full project vision and context
   - `docs/internal/architecture.md` - Project structure and rules
   - `docs/internal/tasks/CLAUDE.md` - Task-specific guidelines

2. Review existing codebase to understand current implementation

### During the Session
1. **Task Selection**
   - Check `docs/internal/tasks/` for available task files
   - Use judgment to prioritize based on:
     - Task complexity (start with simpler tasks)
     - Task dependencies (do prerequisite tasks first)
     - Explicit priority markers in task files (if any)
   - Tasks are intended to be independent unless noted otherwise
   - Taking on complex tasks is good! Don't avoid them, but make sure to put together a plan before doing any major refactor or architectural decisions.

2. **Task Execution**
   - Follow TDD approach: write failing tests first, then implement
   - Follow Hexagonal architecture principles
   - Run unit tests before committing: `uv run pytest tests/unit`
   - ONE task at a time to keep things manageable

3. **Task Completion Flow**
   - Move completed task file to `docs/internal/tasks/done/`
   - Create git commit with descriptive message
   - Ask for user approval before committing
   - Once approved, continue to next task autonomously

4. **Handling Blockers**
   - If blocked with questions, wait for user response
   - Don't pick up new tasks while waiting
   - User will add new tasks to the directory during the session

5. **New Tasks**
   - Periodically check the tasks folder for new files
   - User may add tasks during the session
   - Adapt to new priorities as they emerge

### Guidelines
- **Be Autonomous**: After approval, continue picking up tasks without waiting for instructions
- **Stay Focused**: One task at a time
- **Communicate Clearly**: Provide concise updates on progress
- **Ask When Stuck**: Don't waste time if blocked - ask for clarification
- **Update Documentation**: Always update relevant docs when adding features
- **Ask for approval before moving to next task and marking as done**: Don't move on to next task until user approves. Then you can commit and mark task as done.
- **Do NOT make a static TODO list**: ALWAYS update periodically because new tasks may be added. 

### Session End
The session ends when:
- No more tasks remain in the tasks directory
- User explicitly ends the session
- A complex architectural decision is needed and the user determines to defer the task to later.

## Advanced Variations
- The user may prompt you to implement a larger feature, in this case, they will direct you to a specific subfolder within the tasks folder, which will contain all related tasks.
- In this case, the user will be responsible for specifying order. If none is given, use your best judgement.
- Look for a CLAUDE.md, AGENTS.md, or README.md for a full overview first.