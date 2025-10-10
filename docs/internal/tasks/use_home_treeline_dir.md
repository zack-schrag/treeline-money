Currently, the treeline duckdb file lives in the current directory of whereever the CLI starts. But the saved queries are saved in ~/.treeline folder. Instead, we want everything to be stored in ~/.treeline.

Acceptnace criteria:
- Duckdb file is located in ~/.treeline folder
- Existing db file is manually moved to that folder so I don't have to start from scratch