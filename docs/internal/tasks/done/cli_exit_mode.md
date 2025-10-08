Certain modes are unable to exit without exiting the whole program. /tag mode is good, as it has a "q" command to quit and go back to the main prompt. But others such as /import or /simplefin (not exhaustive) don't have the same exit option. Your goal is to create a consistent and shareable exit option from all modes. 

A potential option for implementation: In Claude Code, for example, ALL input is in the > prompt, there are no inline inputs. Consider something like this, so rather than:
```
Enter your SimpleFIN token: <user input here>
```
It would be like this:
```
Enter your SimpleFIN token:

---
> <user input here>
---
```
Or maybe even:
```
Enter your SimpleFIN token
---
> token here...
---
```
Where the words "token here..." are shown as a subtle preview. The advantage of these, is a user could always exit simply by typing a new slash command. So in the example above, instead of typing a SimpleFIN token, to exit they would just type "/status" or "/help" or something.

Acceptance criteria:
- All user input occurs in the prompt input box for all modes
- /tag mode may require some special handling. If not, implement. If it does need special handling, propose as a new task in docs/internal/tasks
- The implementation is consistent and reusable across all modes and commands, not copy/pasted. Creating a new mode or command with interactive input should be easy to reuse this pattern
