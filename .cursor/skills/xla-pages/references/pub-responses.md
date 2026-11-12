# Saved /pub responses

The preflight reads the public XLA Pages API, but no script makes an HTTP call. The agent makes
the requests and saves each response as is; `scripts/preflight_report.py` reads the saved files.

## Rules

- Only `GET`, and only URLs that start with `https://xla-pages.xsolla.com/pub/`. The `/pub` surface
  is anonymous: send no token, cookie or key. Never call `/integration/*`.
- Save every response, errors included, as one JSON file in the run's folder (for example
  `.xsolla/xla-pub-<UTC time>/`), body unmodified.
- Before any write the oldest response used must be at most 24 hours old. Older ones are
  requested again; `apply_pages.py` refuses otherwise.

## File format

```json
{
  "method": "GET",
  "url": "https://xla-pages.xsolla.com/pub/games/<slug>/core-attributes?project_id=<project id>",
  "requested_at": "2026-11-07T09:00:00Z",
  "status": 200,
  "content_type": "application/json",
  "body": "<the response body as text, exactly as received>"
}
```

`requested_at` is when the request was sent, in UTC with a timezone. `body` is a string, not
parsed JSON, so nothing about the response is changed.

## What to request

Run `preflight_report.py next --pub-dir <folder>`. It prints the URLs still missing; request each,
save it, and run it again until the list is empty. It follows the manifest:

1. The catalog without a mode (the game paths), `mode=buy` and `mode=top_up`, 50 games a page,
   until a page has fewer than 50. The paths read up to 50 pages, a catalog list up to 20.
2. `games/<slug>/core-attributes?project_id=<project id>` for every slug in any catalog, and for a
   slug passed with `--slug`.
3. `media/<cover>/info` for each game's cover.

Then `preflight_report.py report --pub-dir <folder> --batch <batch.json>` prints the report: one
line per game with its failing checks and where to fix them, the redirect list per provider, and
the request time of every response it used.

## Observed response shapes (2026-11-07)

- Success: `{"$schema": "https://xla-pages.xsolla.com/schemas/<Name>.json", "data": …}`.
- Errors are `application/problem+json`: `{"$schema", "title", "status", "detail"}`, for example
  404 `game not found`, 404 `media not found`, 400 `size must be between 1 and 50`.
- A catalog page past the end returns `200` with `"data": []`.
- Media info returns `id`, `name`, `media_type`, `object_name`, `web_object_name`, `content_type`,
  `size`, `object_metadata`, `url`, `created_at`, `updated_at`. For an image cover,
  `object_metadata` was `{}`, not width and height as the manifest says.
