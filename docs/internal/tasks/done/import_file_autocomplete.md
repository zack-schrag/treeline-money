Currently, when in /import mode, the input asks for a file. But there is not help provided to the user to help them find the right file. 

Acceptance criteria:
- When entering file path, provide autocomplete showing suggestions from the current typed path. For example:
```
>: /import

CSV Import

Enter path to CSV file: ~/Do
~/Downloads
~/Documents
```
Where "~/Downloads" and "~/Documents" are suggestions. Make this look nice and allow the user to (optionally) select these if convenient, but don't get in their way.