Currently, the input prompt looks like this:
```
>: /status

📊 Financial Data Status

  Accounts             9    
  Transactions         599  
  Balance Snapshots    9    
  Integrations         1    

Date range: 2025-07-08 to 2025-10-03

Connected Integrations:
  • simplefin

>: 
```
The ">:". Instead, we should make it look like this:
```
---
>
---
```
Where the "---" indicates a subtle horizontal line, similar to how claude code has it. This is a nice sleek look and I want to replicate in Treeline CLI.

Acceptance Criteria:
- Text input in REPL has look described as above.