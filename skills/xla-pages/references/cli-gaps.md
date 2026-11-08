# What XLA Pages still needs from the Xsolla CLI and Shop Builder

For the Xsolla CLI owners and the Shop Builder team. The `xla-pages` skill builds XLA Pages on
x.la in Shop Builder from the [manifest](manifest.yaml). Its preflight, plan, validation and
after-write check work today. An update of an existing page (row text, settings, SEO text, page
look) can run on today's CLI. Creating a page can't: a batch that creates a page stops at the
gate with zero writes.

The Site Builder facts below come from the Site Builder server and Editor code, read
2026-11-08. The Shop Builder team has the file references and tracks the three asks below;
internal references stay out of this public repository.

## Where the commands come from

The `xsolla shopbuilder` commands are being moved from a hand-written spec in the CLI to a spec
Shop Builder generates from its own API: 79 commands, waiting for the next CLI release. In the
generated set the old commands stay but are deprecated, and new ones replace them:

| Deprecated | Use instead |
|---|---|
| `add-block` | `create-block` |
| `get-structure` | `get-full-structure` |
| `update-localization` | `update-translation` |
| `delete-block` | `remove-block` |
| `move-block` | `reorder-blocks` |
| `update-block` (batch) | `patch-block`, `update-page`, `update-theme`; no replacement for `valuesSystem` |

The generated set has the Shop Builder MCP server's capabilities, no more. The three things XLA
Pages need beyond them are the asks below.

## What XLA Pages needs, and what the CLI gives

| Operation | CLI 1.9.4 | Generated CLI |
|---|---|---|
| Read the site with its data connections | `get-structure` | `get-full-structure` |
| Read texts | `get-localization` | `get-localization` |
| Read and write SEO text and the canonical URL | `update-many-localization`; canonical through `update-block` | `get-page-seo`, `update-page-seo` (title, description, ogImage, canonicalUrl), `update-many-localization` |
| Create a static page | `add-page` fails: the server now takes the page path as an object and 1.9.4 sends a string | `add-page --path /payment/klarna` once the string path is accepted again |
| A page on the site theme with no blocks | — | `add-page --type blank` |
| **A dynamic page with a paths provider** (`/game/:slug`) | — | **ask 1** |
| **Connect a value data provider; bind a block field or SEO field** | `update-block` with a `valuesSystem` patch | `update-block`, deprecated; **ask 2** |
| **An `@xla-pages/*` block at an exact version** | — | **ask 3** |
| Delete blocks add-page seeded on a page created in the same run | `update-block` | `remove-block` |
| Hide an optional block, set the page look | `update-block` | `update-block`, deprecated |

## Ask 1: `add-page` with a data provider

```bash
xsolla shopbuilder add-page --slug <domain> --name <name> --path /game/:slug \
  --provider-id ugc-d-paths-games-provider-v2 \
  --provider-input '{"publisherProjectId":"<project id>","locale":"en-US"}'
```

- The server already takes `providerId` and `providerInput` and returns the page with
  `path.connectionId` and `dataConnectionId`. The API docs don't declare the two fields, so the
  generated command has no flags for them.
- A path with one `:param` segment becomes a dynamic path; without a provider it fails clearly.
- The server writes the linked data connection (`ugc-d-data-game-provider-v2`, `slug` bound to
  the route param) in the same request, as the Editor does after creating the page. Until it
  does, the skill writes it itself.

## Ask 2: data connections and bindings

| Command | Does |
|---|---|
| `list-data-connections` | the site's connections with provider, input and `usedBy` |
| `add-data-connection --page-id --data-provider-id --input` | reuses a connection with the same provider and input, or creates one; adds the page to `usedBy` |
| `bind-block-field --block-id --field --connection-id --output` | writes `#VC:<connection>:<output>` to the field, keeps the old value in `preBindValues`, adds the block to `usedBy`; checks the output and the field |
| `unbind-block-field --block-id --field` | restores the old value and removes the usage |
| bound page SEO | the same for a page's title, description and share image |

Until these ship, `update-block` (batch) has to stay: it is the only command that writes
`valuesSystem`. The skill writes connections and bindings through it today.

## Ask 3: a federated block at an exact version

```bash
xsolla shopbuilder create-block --slug <domain> --page-id <page id> \
  --module federated --block-id @xla-pages/hero --block-version 0.2.0 --position 1
```

- Today `create-block` takes an integer version, builds federated blocks only for a few public
  modules from their latest default data, and rejects any other module. The legacy `add-block`
  takes no version.
- Exact means exact: an unknown version is an error with the available versions, never "latest"
  or "latest stable". `@xla-pages/hero` 0.2.0 sorts above every newer build, so a fallback would
  pick an older hero. Pre-releases given exactly are allowed.
- From reading the server code: when a requested federated version doesn't resolve, the server
  falls back to the latest stable version with only a log warning, and a 0.x version never
  resolves. The skill reads every added block back and stops if its version isn't the pinned one.

## Read-back the skill needs

The plan and the check stop, rather than pass, when a read-back lacks one of these:

- the site structure: `valuesSystem.dataProviderConnections`; each page's `path` object with
  `connectionId`, and its `dataConnectionId`; each federated block's `values.blockId` and
  `values.version`; each page's `seo` with its `L:` strings and `canonicalUrl`;
- the localization: `pages.<page id>.texts.<L:id>.{description, translations}`.

The skill tells `@xla-pages/hero` from another `hero` by `values.blockId` holding the scoped
package name. If the blocks service keeps another id for the XLA blocks, the mapping per package
is needed.

## Not verified yet

- That `update-block --data` passes a `valuesSystem` entity to the batch API unchanged.
- That `get-structure` and `get-full-structure` return `valuesSystem`.
- That a page created by add-page has its SEO `L:` strings.
- The blocks-service ids of the `@xla-pages` blocks.
- Whether the CLI's own sign-in gives a token that project-scoped Shop Builder calls accept;
  a known issue makes them return 403 on some accounts.

## Authorization

The skill uses only the Publisher Account session `xsolla auth login` gives the CLI. It never
calls Site Builder's API directly.

## The gate's table

`scripts/cli_gate.py` reads `xsolla <command> --help` and never checks the CLI version number.
This is what it checks today:

| Capability | Command | Flags `--help` must list | CLI 1.9.4 |
|---|---|---|---|
| `add-page` | `shopbuilder add-page` | `--slug`, `--name`, `--path` | yes |
| `add-page-dynamic` | `shopbuilder add-page` | `--provider-id`, `--provider-input` | missing |
| `add-block-pinned` | `shopbuilder add-block` | `--landing-id`, `--page-id`, `--block`, `--package`, `--version`, `--index` | `--package`, `--version` missing |
| `update-block` | `shopbuilder update-block` | `--landing-id`, `--data` | yes |
| `update-many-localization` | `shopbuilder update-many-localization` | `--slug`, `--data` | yes |
| `add-page-blank` (optional) | `shopbuilder add-page` | `--type` | not known |

A plan needs only the capabilities its writes use (`cli_gate.py --plan <plan>`); `cli_gate.py --all`
checks the whole table. When the asks ship, the table and the scripts switch together to the
names they ship with: `create-block` for pinned blocks, `get-full-structure` for the backup and
read-back, and the new connection and binding commands. Until then the gate stays closed for
creates.
