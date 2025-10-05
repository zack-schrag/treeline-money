Currently, when in interactive mode in the CLI (entered by executing 'uv run treeline'), keying up or down displays like this:
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

>: ^[[A 
```

Also, if I have a command typed out, but I want to edit at the beginning, I'm unable to key left to edit the beginning. Here's what a key left looks like:
```
/query select * from transactions^[[D
```

Acceptance criteria:
- Allow keying up and down to go to previous command from interactive mode. In this example, key up would result in "/status" being replaced in the text input
- Allow keying left and right to edit the existing command in the input.