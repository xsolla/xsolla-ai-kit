# Shop Builder expert review checklist

Use this checklist in a 30-minute review with the designated reviewer. Andrey Pyanzin
confirmed that he will review and approve the catalog and presets for SB-8796. Record
the review in the PR or linked Jira issue; do not mark draft evidence as approval.

## Block catalog

- Authoritative inventory confirmed as the Xsolla Web Shop Blocks documentation.
- Confirm the 24 documentation-to-template mappings, especially the
  landing-dependent `leadGameSales`/`lead` mapping and the missing Subscriptions
  template.
- For every module, confirm supported landing types, required data, safe patch paths,
  localization behavior, and catalog/auth dependencies.
- Identify deprecated, internal-only, or template-only modules.
- Review the five palette entries absent from the official inventory and the exported
  `federated` wrapper mapping for Offerwall, Daily rewards, Offer chain, and Social
  quests.

## Presets

Review each preset independently:

| Preset | Questions | Reviewer | Date | Decision / evidence |
|---|---|---|---|---|
| `mobile-single-page` | Is the page/block order a sound mobile default? Is `newStore` the right store block? | Andrey Pyanzin | TBD | Pending |
| `pc-multi-page` | Are Home, Store, and About the right default pages? Are requirements placed correctly? | Andrey Pyanzin | TBD | Pending |
| `live-service-events` | Are Store and Events sufficiently separated? Are bundle/event defaults safe and reusable? | Andrey Pyanzin | TBD | Pending |

For an approval, capture the reviewer's name, team, date, decision, and a durable link
to the PR comment, meeting notes, or Jira comment. Convert requested changes into the
preset or catalog before recording approval.

## Assembly behavior

- Confirm dependency order: theme, pages, navigation, blocks, copy/assets, catalog.
- Confirm that backup output is sufficient for recovery by a Shop Builder engineer.
- Confirm the verification checklist and which failures require manual intervention.
- Confirm that preview is safe and that publication remains a human-only action.
