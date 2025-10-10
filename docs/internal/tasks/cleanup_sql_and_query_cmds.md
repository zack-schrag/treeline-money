Currently, we have 3 commands for executing SQL:
- /query:<query_name>
- /query <single line sql>
- /sql -> which let's you enter multi-line sql

Instead, we should consolidate to a single command: /sql, with the following options:
- /sql -> stays the same, multi-line editor
- /sql <query_name> -> this should do autocomplete for existing queries. For example, if I type "/sql foo_b", it should suggest "foo_bar" and "foo_baz" queries if they are saved.
- /sql <single line sql> -> just executes a single line SQL. For example "/sql select * from transactions limit 10".

Acceptance criteria:
- Implemented as described above
- Old /query commands are removed
