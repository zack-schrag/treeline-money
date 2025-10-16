Right now, tag command is only interactive. We should add a scriptable option to allow users to tag individual items. A use case might a user has a script where they execute a query with "--json" or "--format csv" flags, pipe the results to the tag command to tag all of the given transactions in that query with a set of tags. For example, their script could look like this:
```
treeline query "select * from transactions where ilike '%amazon%'" --format csv | treeline tag online_orders,amazon
```

I don't know the exact right formatting, I'm just trying to convey the concept that a user should be able to script these things. You should consider the best approach here.

Acceptance criteria:
- Approach is approved prior to implementation
- End-user can script tagging individual or many transactions using treeline commands
- New scriptable command follows all other scriptable command patterns (e.g., supporting --json flag, etc.)