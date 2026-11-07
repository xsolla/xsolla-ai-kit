# Xsolla CLI: commands XLA Pages needs

For the Xsolla CLI owners. The `xla-pages` skill builds XLA Pages on x.la in Shop Builder from
the [manifest](manifest.yaml). Its preflight, plan, validation and after-write check work today;
its writes are closed by a gate until the CLI has the commands below.

**The gate** ([`scripts/cli_gate.py`](../scripts/cli_gate.py)) reads `xsolla <command> --help` and
needs the usage line `xsolla shopbuilder <command>` and every flag listed here. It never checks the
CLI version number. If a command ships under another name or flag, change the table in
`cli_gate.py` and this file together.

Conventions for all six, as for the other `shopbuilder` commands: `--json` prints
`{"ok": true, "data": …}`; exit code 10 on HTTP 401/403; no `--force` is ever needed; the command
writes only to the site's draft and never publishes.

## 1. A dynamic page with a paths provider

```text
xsolla shopbuilder add-page --slug <domain> --name <name> --path /game/:slug \
  --paths-provider ugc-d-paths-games-provider-v2 \
  --provider-input '{"publisherProjectId":"<project id>","locale":"en-US"}'
```

- `--path` accepts one `:param` segment for a dynamic page. Today `add-page` allows only a–z, 0–9,
  hyphen and slash.
- Creates the page with that paths provider and creates its linked value provider
  (`ugc-d-data-game-provider-v2`, input `{"slug": "{path}", "publisherProjectId": …}`) the way the
  Editor does.
- Prints `{"_id": "<page id>"}`. Fails with a clear error for an unknown provider or input that
  doesn't match the provider's schema.
- **Read-back** in `get-structure`: `pages[].path` is `{"pathSegment": "/game/:slug", "type":
  "dynamic"}`, and `pages[].dataConnections` lists both connections as
  `{"_id", "provider", "kind": "path" | "value", "input"}`.

## 2. A data connection on a page

```text
xsolla shopbuilder add-data-connection --landing-id <landing id> --page-id <page id> \
  --provider ugc-d-catalog-games-provider-v2 \
  --input '{"publisherProjectId":"<project id>","mode":"top_up"}'
```

- Adds a value data provider to a static or dynamic page. Prints `{"_id": "<connection id>"}`.
- The same provider may be connected twice with different input (`mode: buy` and `mode: top_up`).
- **Read-back:** the connection in `pages[].dataConnections`, as in 1.

## 3. Binding a block field to a provider output

```text
xsolla shopbuilder bind-block-field --landing-id <landing id> --block-id <block id> \
  --field title --connection-id <connection id> --output title
```

- Binds one field of a block to one output of a connection on the same page. Other bindings on
  the block and the page stay as they are.
- Fails when the output isn't one the provider exposes, or the field isn't on the block's version.
- **Read-back:** `pages[].blocks[].bindings` = `{"<field>": {"connection": "<connection id>",
  "output": "<output>"}}`.
- Related, for Site Builder: restoring a saved version currently drops a page's data-provider
  connections, so version history can't serve as a backup for these pages.

## 4. Adding a federated block at an exact version, and reading the version back

```text
xsolla shopbuilder add-block --landing-id <landing id> --page-id <page id> \
  --block federated --package @xla-pages/hero --version 0.2.0 --index 1
```

- Adds exactly that package version. No fallback to "latest" or "latest stable": a version that
  isn't published is an error. A pre-release version given exactly is allowed.
- Why exact: `@xla-pages/hero` 0.2.0 sorts above every newer build, so a "latest stable" fallback
  would pick an older hero.
- Prints `{"_id": "<block id>"}`.
- **Read-back:** the federated block's `values.package` (the scoped name, `@xla-pages/hero`) and
  `values.version`. Today exports carry only an unscoped `values.blockId` and `values.version`, so
  `@xla-pages/hero` can't be told apart from another `hero`.

## 5. Page SEO fields

```text
xsolla shopbuilder set-page-seo --landing-id <landing id> --page-id <page id> --field title --value "Top up with Klarna"
xsolla shopbuilder set-page-seo --landing-id <landing id> --page-id <page id> --field title \
  --connection-id <connection id> --output title
```

- `--field` is `title`, `description`, `image` or `canonical`. Either `--value` (static text) or
  `--connection-id` and `--output` (bound to a provider output on the same page).
- On a dynamic page a `canonical` value may hold the path parameter: `https://x.la/game/{slug}`.
- **Read-back:** `pages[].seo.<field>` = `{"value": "<text>"}` or
  `{"connection": "<connection id>", "output": "<output>"}`. Today `seo.title`, `seo.description`
  and `seo.ogImage` hold localization IDs and there is no `canonical`.

## 6. A page without seeded blocks

```text
xsolla shopbuilder add-page --slug <domain> --name <name> --path /payment/klarna --empty
```

- Creates the page with no blocks and on the site theme. Today `add-page` seeds the template's
  standard blocks and gives the page its own theme copy.
- Optional for the gate: without `--empty`, the skill deletes the blocks `add-page` seeded on a page
  it created in the same run, with a page-level `update-block` remove patch, and sets the page look
  to the reference page's values.

## The gate's table

| Capability | Command | Flags `--help` must list |
|---|---|---|
| `add-page` | `shopbuilder add-page` | `--slug`, `--name`, `--path` |
| `add-page-dynamic` | `shopbuilder add-page` | `--paths-provider`, `--provider-input` |
| `add-block-pinned` | `shopbuilder add-block` | `--landing-id`, `--page-id`, `--block`, `--package`, `--version`, `--index` |
| `update-block` | `shopbuilder update-block` | `--landing-id`, `--data` |
| `add-data-connection` | `shopbuilder add-data-connection` | `--landing-id`, `--page-id`, `--provider`, `--input` |
| `bind-block-field` | `shopbuilder bind-block-field` | `--landing-id`, `--block-id`, `--field`, `--connection-id`, `--output` |
| `set-page-seo` | `shopbuilder set-page-seo` | `--landing-id`, `--page-id`, `--field`, `--value`, `--connection-id`, `--output` |
| `add-page-empty` (optional) | `shopbuilder add-page` | `--empty` |

A plan needs only the capabilities its writes use (`cli_gate.py --plan <plan>`); `cli_gate.py
--all` checks the whole table.
