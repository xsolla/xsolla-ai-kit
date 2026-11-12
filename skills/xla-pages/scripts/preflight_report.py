#!/usr/bin/env python3
"""The XLA Pages preflight, from /pub responses the agent saved. This script makes no HTTP calls.

  next    the GET URLs still missing from the saved responses
  report  one line per game: the failing checks and where to fix them, with request times

Saved response format: references/pub-responses.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit

SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import xla_common as common  # noqa: E402

PUB_PREFIX = "https://xla-pages.xsolla.com/pub/"
PAGE_SIZE = 50
CATALOG_MODES = (None, "buy", "top_up")
# The paths provider reads up to 50 catalog pages; a catalog list block shows up to 20.
MAX_PAGES = {None: 50, "buy": 20, "top_up": 20}
TITLE_LIMIT = 60
SHORT_DESCRIPTION_LIMIT = 150
MEDIA_LIMIT = 20
CLOCK_SKEW = timedelta(minutes=5)


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else None


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return f"{parts.scheme}://{parts.netloc}{parts.path}" + (f"?{query}" if query else "")


def catalog_url(project_id: int, mode: str | None, page: int) -> str:
    query = {"publisher_project_id": str(project_id), "page": str(page), "size": str(PAGE_SIZE)}
    if mode:
        query["mode"] = mode
    return normalize_url(PUB_PREFIX + "catalog/games?" + urlencode(query))


def game_url(slug: str, project_id: int) -> str:
    return normalize_url(PUB_PREFIX + f"games/{quote(slug, safe='')}/core-attributes?project_id={project_id}")


def media_url(media_id: str) -> str:
    return normalize_url(PUB_PREFIX + f"media/{quote(media_id, safe='')}/info")


# --------------------------------------------------------------------------- bundle


def load_bundle(directory: Path) -> tuple[dict[str, dict], list[str]]:
    """Read every saved response. Returns {normalized URL: response} and the errors found."""
    responses: dict[str, dict] = {}
    errors: list[str] = []
    files = sorted(Path(directory).glob("*.json"))
    if not files:
        errors.append(f"{directory} holds no saved /pub responses")
    for path in files:
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: not JSON ({exc})")
            continue
        problem = saved_problem(saved)
        if problem:
            errors.append(f"{path.name}: {problem}")
            continue
        saved = {**saved, "file": path.name, "moment": parse_time(saved["requested_at"])}
        key = normalize_url(saved["url"])
        if key not in responses or saved["moment"] > responses[key]["moment"]:
            responses[key] = saved
    return responses, errors


def saved_problem(saved: object) -> str | None:
    if not isinstance(saved, dict):
        return "must be a JSON object"
    if saved.get("method") != "GET":
        return "method must be GET"
    url = saved.get("url")
    if not isinstance(url, str) or not url.startswith(PUB_PREFIX):
        return f"url must start with {PUB_PREFIX}"
    if parse_time(saved.get("requested_at")) is None:
        return "requested_at must be an ISO 8601 time with a timezone"
    status = saved.get("status")
    if not isinstance(status, int) or isinstance(status, bool):
        return "status must be the HTTP status code"
    if not isinstance(saved.get("body"), str):
        return "body must be the response body as text, saved as is"
    return None


def body_data(saved: dict | None) -> object:
    if not saved or saved["status"] != 200:
        return None
    try:
        body = json.loads(saved["body"])
    except json.JSONDecodeError:
        return None
    return body.get("data") if isinstance(body, dict) else None


# --------------------------------------------------------------------------- what to fetch


def catalog_state(responses: dict, project_id: int, mode: str | None) -> tuple[list[dict], str | None, bool]:
    """(tiles read so far, next URL to fetch or None, whether the limit cut the list)."""
    tiles: list[dict] = []
    for page in range(1, MAX_PAGES[mode] + 1):
        url = catalog_url(project_id, mode, page)
        saved = responses.get(url)
        if saved is None:
            return tiles, url, False
        items = body_data(saved)
        if saved["status"] != 200 or not isinstance(items, list):
            return tiles, None, False
        tiles.extend(item for item in items if isinstance(item, dict))
        if len(items) < PAGE_SIZE:
            return tiles, None, False
    return tiles, None, True


def known_slugs(responses: dict, catalogs: dict, extra: list[str]) -> list[str]:
    slugs: dict[str, None] = {}
    for tiles in catalogs.values():
        for tile in tiles:
            if isinstance(tile.get("slug"), str):
                slugs[tile["slug"]] = None
    for slug in extra:
        slugs[slug] = None
    for url in responses:
        match = re.fullmatch(re.escape(PUB_PREFIX) + r"games/([^/?]+)/core-attributes(\?.*)?", url)
        if match:
            slugs[unquote(match.group(1))] = None
    return list(slugs)


def next_urls(responses: dict, project_id: int, extra_slugs: list[str]) -> list[str]:
    missing = []
    catalogs = {}
    for mode in CATALOG_MODES:
        tiles, url, _ = catalog_state(responses, project_id, mode)
        catalogs[mode] = tiles
        if url:
            missing.append(url)
    for slug in known_slugs(responses, catalogs, extra_slugs):
        url = game_url(slug, project_id)
        game = body_data(responses.get(url))
        if url not in responses:
            missing.append(url)
        elif isinstance(game, dict) and isinstance(game.get("cover"), str) and game["cover"]:
            cover = media_url(game["cover"])
            if cover not in responses:
                missing.append(cover)
    return missing


# --------------------------------------------------------------------------- checks


def check_game(slug: str, game: dict | None, cover: dict | None, modes: dict[str, dict | None],
               in_paths: bool, manifest_checks: list[dict]) -> list[dict]:
    on_fail = {i: entry.get("on_fail", "") for i, entry in enumerate(manifest_checks)}
    failures = []

    def fail(index: int, detail: str) -> None:
        failures.append({"check": manifest_checks[index]["check"], "detail": detail, "on_fail": on_fail[index]})

    if not common.SLUG_RE.fullmatch(slug):
        fail(0, f"slug {slug!r} has characters other than a-z, 0-9 and -")
    if not (modes.get("buy") or modes.get("top_up")):
        detail = "the game is in neither the buy nor the top_up catalog"
        if in_paths:
            detail += " (it still gets a path: the paths provider reads the catalog without a mode filter)"
        fail(1, detail)
    if game is None:
        return failures
    title = game.get("title") if isinstance(game.get("title"), str) else ""
    if not title.strip() or len(title) > TITLE_LIMIT:
        fail(2, f"title is {len(title)} characters (1 to {TITLE_LIMIT})" if title.strip() else "title is empty")
    short = game.get("short_description") if isinstance(game.get("short_description"), str) else ""
    if len(short) > SHORT_DESCRIPTION_LIMIT:
        fail(3, f"short_description is {len(short)} characters (max {SHORT_DESCRIPTION_LIMIT})")
    if not game.get("cover"):
        fail(4, "the game has no cover")
    elif cover is None or cover["status"] != 200:
        fail(4, f"cover info returned HTTP {cover['status'] if cover else 'not fetched'}")
    else:
        info = body_data(cover) or {}
        content_type = info.get("content_type") if isinstance(info, dict) else None
        if not (isinstance(content_type, str) and content_type.startswith("image/")):
            fail(4, f"cover content_type is {content_type!r}")
    if modes.get("buy") is not None:
        if not game.get("game_key_sku"):
            fail(5, "game_key_sku is empty")
        tile_price = (modes["buy"] or {}).get("key_price")
        if not (isinstance(tile_price, dict) and tile_price.get("amount")) and not game.get("game_key_price"):
            fail(6, "neither the catalog key_price nor game_key_price is set")
    if not game.get("faq"):
        fail(7, "faq is empty")
    media = game.get("media") if isinstance(game.get("media"), list) else []
    if len(media) > MEDIA_LIMIT:
        fail(8, f"media has {len(media)} items")
    return failures


def payable_with(game: dict, provider: str) -> int:
    """How many payment_methods entries name the provider (0 = not payable). Empty = any."""
    methods = game.get("payment_methods")
    if not methods:
        return -1
    return sum(
        1
        for method in methods
        if isinstance(method, dict) and str(method.get("id", "")).lower() == provider.lower()
    )


def report(responses: dict, bundle_errors: list[str], manifest: dict, config: dict,
           providers: list[str], extra_slugs: list[str], now: datetime) -> dict:
    project_id = config["project_id"]
    preflight = manifest["preflight"]
    max_age = float(preflight.get("max_age_hours_before_write", 24))
    catalogs, cut = {}, []
    for mode in CATALOG_MODES:
        tiles, _, truncated = catalog_state(responses, project_id, mode)
        catalogs[mode] = tiles
        if truncated:
            cut.append(mode or "no mode")
    missing = next_urls(responses, project_id, extra_slugs)
    by_mode = {mode: {t["slug"]: t for t in catalogs[mode] if isinstance(t.get("slug"), str)} for mode in CATALOG_MODES}

    used: dict[str, dict] = {}
    for mode in CATALOG_MODES:
        for page in range(1, MAX_PAGES[mode] + 1):
            url = catalog_url(project_id, mode, page)
            if url in responses:
                used[url] = responses[url]

    games, lines, redirects = [], [], []
    for slug in known_slugs(responses, catalogs, extra_slugs):
        game_saved = responses.get(game_url(slug, project_id))
        game = body_data(game_saved)
        cover_saved = None
        if game_saved:
            used[game_url(slug, project_id)] = game_saved
        if isinstance(game, dict) and isinstance(game.get("cover"), str) and game["cover"]:
            cover_saved = responses.get(media_url(game["cover"]))
            if cover_saved:
                used[media_url(game["cover"])] = cover_saved
        modes = {mode: by_mode[mode].get(slug) for mode in ("buy", "top_up")}
        in_paths = slug in by_mode[None]
        entry = {
            "slug": slug,
            "in_paths": in_paths,
            "modes": [mode for mode, tile in modes.items() if tile is not None],
            "requested_at": game_saved["requested_at"] if game_saved else None,
            "failures": [],
            "providers": {},
        }
        if game_saved is None:
            entry["failures"].append({"check": "core-attributes", "detail": "not fetched yet", "on_fail": "fetch it"})
        elif game_saved["status"] != 200 or not isinstance(game, dict):
            entry["failures"].append({
                "check": "core-attributes",
                "detail": f"HTTP {game_saved['status']}",
                "on_fail": "no data for this game; fix in the API",
            })
        entry["failures"].extend(check_game(
            slug, game if isinstance(game, dict) else None, cover_saved, modes,
            in_paths, preflight["per_game"],
        ))
        provider_rule = preflight["per_provider_and_game"][0]
        not_payable = []
        for provider in providers:
            if not isinstance(game, dict):
                continue
            count = payable_with(game, provider)
            entry["providers"][provider] = "any provider" if count < 0 else count
            if count == 0:
                not_payable.append(provider)
                if in_paths:
                    redirects.append({"provider": provider, "slug": slug})
        games.append(entry)
        parts = [f"{f['detail']} → {f['on_fail']}" for f in entry["failures"]]
        if not_payable:
            parts.append(f"not payable with {', '.join(not_payable)} → {provider_rule['on_fail']}")
        lines.append(f"{slug}: " + ("; ".join(parts) if parts else "ok"))

    moments = [saved["moment"] for saved in used.values()]
    oldest = min(moments) if moments else None
    newest = max(moments) if moments else None
    future = [saved["file"] for saved in used.values() if saved["moment"] > now + CLOCK_SKEW]
    age_hours = round((now - oldest).total_seconds() / 3600, 2) if oldest else None
    complete = not bundle_errors and not missing and not future
    fresh_until = iso(oldest + timedelta(hours=max_age)) if oldest else None
    header = (
        f"Responses requested {iso(oldest)} to {iso(newest)}; the oldest is {age_hours} h old, "
        f"so writes may use them until {fresh_until} ({max_age:g} h)."
        if oldest
        else "No responses used."
    )
    return {
        "ok": complete,
        "complete": complete,
        "errors": bundle_errors + [f"{name}: requested in the future" for name in future],
        "missing": missing,
        "catalog_limit_reached": cut,
        "requested_at": {"oldest": iso(oldest) if oldest else None, "newest": iso(newest) if newest else None},
        "now": iso(now),
        "age_hours": age_hours,
        "max_age_hours": max_age,
        "fresh_until": fresh_until,
        "fresh_for_write": bool(oldest) and complete and (now - oldest) <= timedelta(hours=max_age),
        "responses": sorted(
            ({"url": url, "requested_at": s["requested_at"], "status": s["status"]} for url, s in used.items()),
            key=lambda r: r["url"],
        ),
        "games": games,
        "redirects": redirects,
        "lines": [header] + lines,
    }


def batch_providers(path: Path | None) -> list[str]:
    if path is None:
        return []
    batch = common.load_json(path, "batch")
    rows = batch.get("providers") if isinstance(batch, dict) else None
    if not isinstance(rows, list):
        raise ValueError("the batch must have a providers list")
    return [row["provider"] for row in rows if isinstance(row, dict) and isinstance(row.get("provider"), str)]


def build_report(pub_dir: Path, config: dict, providers: list[str], now: datetime,
                 manifest: dict | None = None, extra_slugs: list[str] | None = None) -> dict:
    manifest = manifest or common.load_manifest()
    responses, errors = load_bundle(pub_dir)
    return report(responses, errors, manifest, config, providers, list(extra_slugs or []), now)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("next", "report"))
    parser.add_argument("--pub-dir", required=True, type=Path, help="the saved /pub responses")
    parser.add_argument("--config", type=Path, default=common.DEFAULT_CONFIG, help="local .xsolla/xla-pages.json")
    parser.add_argument("--batch", type=Path, help="the batch file; its providers are checked per game")
    parser.add_argument("--slug", action="append", default=[], help="a game to check besides the catalog's")
    parser.add_argument("--now", help="ISO time to judge the age against (tests); default: now")
    args = parser.parse_args(argv)
    try:
        manifest = common.load_manifest()
        config = common.load_config(args.config)
        if args.action == "next":
            responses, errors = load_bundle(args.pub_dir) if args.pub_dir.exists() else ({}, [])
            output = {
                "errors": [e for e in errors if "holds no saved" not in e],
                "next": next_urls(responses, config["project_id"], args.slug),
            }
            print(json.dumps(output, indent=2))
            return 1 if output["errors"] else 0
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
        if now is None:
            raise ValueError("--now must be an ISO time with a timezone")
        result = build_report(args.pub_dir, config, batch_providers(args.batch), now, manifest, args.slug)
    except (OSError, ValueError) as exc:
        print(f"Preflight failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
