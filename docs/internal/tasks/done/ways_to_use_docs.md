Add external facing documentation in docs/external for showing "Ways to Use". This is documenting things that don't necessarily exist in the implementation yet, we are basically documenting how things should work. 

This document should describe the different options users have for using Treeline:
- As the CLI (the standard way which is documented well already)
- As an MCP server. For example, if they use Claude already, they could simply use the Treeline MCP server and interact with Claude instead of the Treeline CLI directly.
- By hooking up a marimo or jupyter notebook to the duckdb instance directly
- By using a SQL UI tool (maybe show DBeaver as an example or something)
- If you have other ideas here, feel free to add.

The idea here is to document the flexibility users have, so they can still access and interact with their data without being forced into a particular interface. We get the data and provide access to it, but users can have direct access to it. Make sure to highlight any warnings if they do any "write" and edit commands to the data, it could cause issues, especially schema updates.

Acceptance criteria:
- Documentation exists outlining ways to use mentioned above in docs/external in the appropriate folder.