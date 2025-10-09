Currently, we can save queries in /sql to disk. But we can't load them to execute them. Add an option within the /sql mode to load a saved query and execute it.

Acceptance criteria:
- User can select a saved query to load into the prompt
- User can edit the loaded query before executing
- User is provided autocomplete suggestions from saved queries as they type (see other autocomplete solutions for this project in /import and main slash commands)
- User can choose to either save as a new query or overwrite an existing saved query. This can simply be via a autocomplete suggestions. If they select a suggested autocomplete file, then overwrite. Otherwise it's a new one
