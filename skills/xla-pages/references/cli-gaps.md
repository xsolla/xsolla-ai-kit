# What XLA Pages still needs from the Xsolla CLI and Site Builder

For the Xsolla CLI owners and the Shop Builder team. The `xla-pages` skill builds XLA Pages on
x.la in Shop Builder from the [manifest](manifest.yaml). Its preflight, plan, validation and
after-write check work today. Its writes go through the commands the CLI already has wherever
Site Builder's API allows it; two CLI changes and one server change are left. Until then, a
batch that creates a page stops at the gate with zero writes. An update of an existing page
(row text, settings, SEO text, page look) runs today.

The Site Builder facts below come from the Site Builder server and Editor code, read
2026-11-08. The Shop Builder team has the file references; they stay out of this public
repository.

## Already possible with today's commands

| Operation | Command | How Site Builder stores it |
|---|---|---|
| Connect a value data provider to a page (the catalog with `mode: buy` or `top_up`) | `update-block`, entity `valuesSystem` | `{"type": "valuesSystem", "id": "current-values-system", "patches": [{"op": "add", "path": ["dataProviderConnections", "<id>"], "value": {"id", "dataProviderId", "input", "usedBy": ["page:<page id>"]}}]}`. A connection with the same provider and input is reused: only `page:<id>` is added to its `usedBy` |
| The linked game-data connection of a dynamic page | `update-block`, entity `valuesSystem` | `{"id": <page.dataConnectionId>, "dataProviderId": "ugc-d-data-game-provider-v2", "input": {"slug": "#VC:conn-route-params:slug", "publisherProjectId": …}, "usedBy": ["page:<id>"]}`, written by the Editor client after add-page |
| Bind a block field to a provider output | `update-block`, entities `block` and `valuesSystem` in one batch | The field holds `"#VC:<connection id>:<output>"` in `values.internalBlockValues.<field>`, its previous value moves to `values.preBindValues.<field>`, and `block:<id>` joins the connection's `usedBy` |
| SEO title, description and share image | `update-many-localization` | The page's `seo.title`, `seo.description` and `seo.ogImage` hold `L:` strings; a bound one holds `"#VC:…"` in its text, and the page joins the connection's `usedBy` |
| Canonical URL | `update-block`, entity `page`, path `["seo", "canonicalUrl"]` | A plain string in the page's `seo` |
| Settings and row content, hiding an optional block, the page look, deleting blocks add-page seeded in the same run | `update-block` | Block and page patches, as the kit's other Shop Builder skills use them |

## What the CLI must add

These are the commands and flags the skill's gate ([`scripts/cli_gate.py`](../scripts/cli_gate.py)) looks
for in `--help`. It never checks the CLI version number.

### 1. add-page: a dynamic page with a paths provider

```bash
xsolla shopbuilder add-page --slug <domain> --name <name> --path /game/:slug \
  --provider-id ugc-d-paths-games-provider-v2 \
  --provider-input '{"publisherProjectId":"<project id>","locale":"en-US"}'
```

- The server already takes these fields: `POST /merchant/:merchantId/project/:projectId/landing/:domain/pages`
  with `path: {"type": "dynamic", "pathSegment": "/game/:slug"}`, `providerId` and `providerInput`.
  It creates or reuses the paths connection and the route-params connection, and returns the page with
  `path.connectionId` and `dataConnectionId`.
- The CLI must accept one `:param` segment in `--path` (today: a–z, 0–9, `-` and `/`) and send the path
  object and the two fields.
- Optional, used when present: `--type blank`. A blank page is on the site theme and, on a site with a
  common layout, has no blocks. Without it, the skill deletes the blocks add-page seeded on a page it created in the same run.

### 2. add-block: a federated block at an exact version

```bash
xsolla shopbuilder add-block --landing-id <landing id> --page-id <page id> \
  --block federated --package <blocks-service id> --version 0.2.0 --index 1
```

- Adds exactly that version, never "latest" or "latest stable". `@xla-pages/hero` 0.2.0 sorts above
  every newer build, so a fallback would pick an older hero. A pre-release given exactly is allowed.
- Today `add-block` calls the legacy `POST …/ui/{landing}/page/{pageId}/block` with `{block, index}`,
  which has no version. The block resource `POST …/landing/:domain/pages/:pageId/blocks` takes `module`,
  `version`, `position` and `blockValues`, but builds public federated modules from the latest catalog
  entry.
- Prints `{"_id": "<block id>"}`. The skill reads the block back and stops if its version isn't the
  pinned one.

## What the Site Builder server must change

- **No silent fallback.** When the requested version of a federated block isn't found, the server
  falls back to the latest stable version. For an exact add, an unknown version must be an error.
- **XLA blocks through the block resource.** Creating a federated block that isn't one of the public
  modules at a given version.
- Not needed by the skill: auto-upgrades. The server never moves a 0.x version or a pre-release,
  and the `@xla-pages` blocks are 0.x.

## Read-back the skill needs

The plan and the check stop, rather than pass, when a read-back lacks one of these:

- `get-structure`: `valuesSystem.dataProviderConnections`; each page's `path` object with `connectionId`
  and its `dataConnectionId`; each federated block's `values.blockId` and `values.version`; each page's
  `seo` with its `L:` strings and `canonicalUrl`.
- `get-localization`: `pages.<page id>.texts.<L:id>.{description, translations}`.
- The skill tells `@xla-pages/hero` from another `hero` by `values.blockId` holding the scoped package
  name. If the blocks service keeps another id for the XLA blocks, the mapping per package is needed.

## Not verified yet

- That `xsolla shopbuilder update-block` passes `"type": "valuesSystem"` through to the batch API unchanged.
- That the CLI's `get-structure` returns `valuesSystem`.
- That a page created by add-page has its SEO `L:` strings.
- The blocks-service ids of the `@xla-pages` blocks.
- Whether the server's add-page will also write the linked data connection (the Editor client does today;
  the skill writes it when it is missing).

## Authorization

The skill uses only the Publisher Account session `xsolla auth login` gives the CLI. It never calls
Site Builder's API directly.

## The gate's table

| Capability | Command | Flags `--help` must list | Today |
|---|---|---|---|
| `add-page` | `shopbuilder add-page` | `--slug`, `--name`, `--path` | yes |
| `add-page-dynamic` | `shopbuilder add-page` | `--provider-id`, `--provider-input` | missing |
| `add-block-pinned` | `shopbuilder add-block` | `--landing-id`, `--page-id`, `--block`, `--package`, `--version`, `--index` | `--package`, `--version` missing |
| `update-block` | `shopbuilder update-block` | `--landing-id`, `--data` | yes |
| `update-many-localization` | `shopbuilder update-many-localization` | `--slug`, `--data` | yes |
| `add-page-blank` (optional) | `shopbuilder add-page` | `--type` | not known |

A plan needs only the capabilities its writes use (`cli_gate.py --plan <plan>`); `cli_gate.py --all`
checks the whole table.
