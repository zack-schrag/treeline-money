- [ ] Revamp the terminal UI.
Use Textual and make a much richer and dynamic terminal UI. Come up with a proposal identifying what widgets you'd use and put your proposal in docs/internal. Review PRFAQ.md and all docs in docs/ folder to make sure you understand the vision of the project.

- [ ] Implement tagging power mode.
Requirements:
  - Users should be able to rapidly tag transactions with suggested tags. We should abstract the suggested tags functionality. For now, we can just suggest the most frequently used tags, but abstract it so we can easily add other algorithms for suggested tags.
  - Users should not be forced to do one transaction before moving to the next. Users should be able to freely key up and down rapidly through transactions and use keyboard shortcuts for quick tagging
  - Consider which textual widgets would be most appropriate for this power mode.
  - Come up with a proposal and put in docs/internal before coding.

- [ ] Implement CSV importing.
Requirements:
    - Users should be able to import CSV transactions by selecting a local file
    - Transactions must be deduped. External IDs won't be enough here, because we need deduping across different providers (CSV and SimpleFIN). But this logic should be abstracted appropriately using our hexagonal principles.
    - Come up with a proposal and put in docs/internal before coding.