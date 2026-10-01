#!/usr/bin/env python3
"""Reference implementation — Catalog translation CSV round-trip (stateless).

Part of the `localization` skill. The AGENT runs this via Bash; the user never
types the command. Deterministic CSV codec + safe write so the model doesn't
hand-assemble CSV at scale — the model translates, this moves data.

The script OWNS the CSV file so the model never serializes it at scale. For AI
translation, loop: `batch` (get N empty rows) -> model translates -> `fill` (write
them in) -> repeat -> `check` -> `import`.

CSV is wide, one row per translatable string:
  entity, id, subid, field, context, <source>, <locale...>
  - entity: items | groups | virtual_currency | vc_package | bundle | value_points | attribute
  - id:     sku, or external_id (groups, attribute)
  - subid:  "" normally; for attribute VALUES it is the value external_id
  - field:  name | description | long_description | value
  - empty target cell = missing (needs translation)

Catalog update REPLACES the object, so import does GET -> merge -> PUT full state
(pass-through: every field the GET returned goes back, minus server-derived ones).
No sidecar/state: `missing` is derived; existing values are never overwritten
unless --overwrite is passed.

`import` PREVIEWS by default and writes only with --write, so a forgotten flag
cannot damage a catalog. It refuses unknown locales up front (an unknown locale
404s and drops the whole PUT) and reports what was actually written, not what it
intended to write (exit 1 if any object failed).

Credentials (no hardcoded paths): from the environment, or a .env file via
--env PATH / $XSOLLA_ENV_FILE. Required: XSOLLA_PROJECT_ID, XSOLLA_PROJECT_API_KEY
(XSOLLA_MERCHANT_ID optional, used as an auth fallback).

Usage:
  discover: catalog_i18n.py discover [--env PATH]
  langs:    catalog_i18n.py langs [--env PATH]
  export:   catalog_i18n.py export <out.csv> [locales=ru,de] [--source en]
                                     [--entity items,groups,...] [--missing] [--env PATH]
  batch:    catalog_i18n.py batch <csv> --locale de [--size 50]
  fill:     catalog_i18n.py fill  <csv> --locale de [--from FILE|-]
  merge:    catalog_i18n.py merge <csv> --from <partner.csv> [--overwrite]
  check:    catalog_i18n.py check <csv> [--max-len N | --max-len name=30,description=200]
                                     [--source en]
  import:   catalog_i18n.py import <in.csv> [--source en] [--write] [--overwrite]
                                     [--allow-field-loss]
                                            [--pace 0.25] [--snapshot PATH|--no-snapshot]
                                            [--on-conflict skip|overwrite] [--no-verify]
                                            [--backup PATH|--no-backup] [--env PATH]
            (no --write = preview; --dry is accepted as an explicit alias for it)
  restore:  catalog_i18n.py restore <snapshot.json> [--write] [--env PATH]
"""
import base64, csv, json, os, re, sys, time, urllib.request, urllib.error

API_BASE = "https://store.xsolla.com/api"
# Catalog entities live on v2; LiveOps promotions on v3. Each entity says which via
# its "api" key, defaulting to v2 — probing /v2/admin/promotions* is what produced a
# spurious "403 endpoint forbidden" and the belief that LiveOps needed a special key.
# How much of an error body to keep. Xsolla reports schema rejections in
# `errorMessageExtended`, a list that sits AFTER the generic message, so a short
# cap throws away the only part that says what was actually wrong.
ERROR_BODY_CHARS = 2000

# Flat entities: address = (id). Add new ones here once their admin endpoints are
# confirmed. Content-bearing entities set "content": True.
ENTITIES = {
    "items": {"list": "/admin/items/virtual_items", "path": "/admin/items/virtual_items/sku/{id}",
              "id": "sku", "fields": ["name", "description", "long_description"],
              # PUT rejects an item whose `description` is merely absent, so a null
              # one has to be sent through explicitly. Measured, per entity — see
              # ALWAYS_SEND in _put_body.
              "always_send": ["description"],
              "keep": ["sku", "name", "description", "long_description", "virtual_item_type",
                       "prices", "vc_prices", "is_free", "is_enabled", "is_show_in_store",
                       "order", "limits", "regions", "attributes"]},
    "groups": {"list": "/admin/items/groups", "path": "/admin/items/groups/{id}",
               "id": "external_id", "fields": ["name", "description"],
               "keep": ["external_id", "name", "description"]},
    "virtual_currency": {"list": "/admin/items/virtual_currency", "path": "/admin/items/virtual_currency/sku/{id}",
                         "id": "sku", "fields": ["name", "description", "long_description"],
                         "keep": ["sku", "name", "description", "long_description", "prices", "vc_prices",
                                  "is_free", "is_enabled", "is_show_in_store", "order", "limits",
                                  "regions", "attributes", "is_hard", "is_paid_randomized_reward"]},
    "vc_package": {"list": "/admin/items/virtual_currency/package", "path": "/admin/items/virtual_currency/package/sku/{id}",
                   "id": "sku", "fields": ["name", "description", "long_description"], "content": True,
                   "keep": ["sku", "name", "description", "long_description", "content", "prices",
                            "is_free", "is_enabled", "is_show_in_store", "order", "limits", "regions", "attributes"]},
    "bundle": {"list": "/admin/items/bundle", "path": "/admin/items/bundle/sku/{id}",
               "id": "sku", "fields": ["name", "description", "long_description"], "content": True,
               "keep": ["sku", "name", "description", "long_description", "content", "prices",
                        "is_free", "is_enabled", "is_show_in_store", "order", "limits", "regions", "attributes"]},
    "value_points": {"list": "/admin/items/value_points", "path": "/admin/items/value_points/sku/{id}",
                     "id": "sku", "fields": ["name", "description", "long_description"],
                     "keep": ["sku", "name", "description", "long_description", "is_enabled", "order", "is_clan"]},
    "game": {"list": "/admin/items/game", "path": "/admin/items/game/sku/{id}",
             "drop_if_empty": ["periods"],
             "id": "sku", "fields": ["name", "description", "long_description"], "unit_items": True,
             "keep": ["sku", "name", "description", "long_description", "unit_items", "is_enabled",
                      "is_show_in_store", "order", "attributes"]},

    # --- LiveOps. Different API version and different paths from the catalog, which
    # is why probing /v2/admin/promotions* returned 403 and looked like a permissions
    # problem: the endpoints are /v3/admin/promotion|coupon|promocode|unique_catalog_offer
    # and /v2/admin/daily_chain|offer_chain, and a project key reads all of them.
    #
    # `write_unverified` marks an entity whose WRITE form has never been exercised
    # against a live object. Reading, exporting, translating and QA are harmless and
    # fully enabled; only `import --write` refuses, because a PUT here replaces the
    # object and the required-even-when-null / must-be-stripped rules are measured per
    # entity, never guessed. Clear the flag once a create -> localize -> verify ->
    # restore run has been done for that entity.
    "discount_promotion": {"list": "/admin/promotion/item", "path": "/admin/promotion/{id}/item",
                           "derived": ["id"],
                           "api": "v3", "id": "id", "fields": ["name"],
                           "keep": ["id", "name", "is_enabled", "discount", "items", "limits",
                                    "promotion_periods", "attribute_conditions"]},
    "bonus_promotion": {"list": "/admin/promotion/bonus", "path": "/admin/promotion/{id}/bonus",
                        "derived": ["id"],
                        "api": "v3", "id": "id", "fields": ["name"],
                        "keep": ["id", "name", "is_enabled", "bonus", "condition",
                                 "promotion_periods", "attribute_conditions"]},
    "promocode": {"list": "/admin/promocode", "path": "/admin/promocode/{id}",
                  "derived": ["is_enabled", "external_id", "total_codes_count"],
                  "api": "v3", "id": "external_id", "fields": ["name"],
                  "keep": ["external_id", "name", "is_enabled", "bonus", "discount",
                           "discounted_items", "promotion_periods", "redeem_code_limit",
                           "redeem_total_limit", "redeem_user_limit"]},
    "coupon": {"list": "/admin/coupon", "path": "/admin/coupon/{id}",
               "api": "v3", "id": "external_id", "fields": ["name"],
               "derived": ["is_enabled", "external_id", "total_codes_count"],
               "keep": ["external_id", "name", "is_enabled", "bonus", "discount",
                        "promotion_periods"]},
    "unique_catalog_offer": {"list": "/admin/unique_catalog_offer",
                             "path": "/admin/unique_catalog_offer/{id}",
                             "api": "v3", "id": "external_id", "fields": ["name"],
                             "derived": ["is_enabled", "external_id", "total_codes_count"],
                             "keep": ["external_id", "name", "is_enabled", "promotion_periods"]},
    "daily_chain": {"list": "/admin/daily_chain", "path": "/admin/daily_chain/id/{id}",
                    "no_write_while_active": "is_enabled",
                    "derived": ["number_of_steps"], "always_send": ["type"],
                    "id": "id", "fields": ["name", "description"],
                    "keep": ["id", "name", "description", "is_enabled", "is_recurrent",
                             "date_start", "date_end", "steps", "order", "type"]},
    # The value-point mechanic ("collect points, unlock steps"). Carries more
    # localizable text than anything else in the catalog: five top-level fields plus a
    # name on every step. Unlike attributes, the steps ride inside the object's own PUT,
    # so this stays a flat entity with a `nested` block rather than needing its own
    # write path. Measured 2026-09-08.
    "reward_chain": {"list": "/admin/reward_chain", "path": "/admin/reward_chain/id/{id}",
                     "id": "reward_chain_id",
                     "fields": ["name", "description", "long_description",
                                "popup_header", "popup_instruction"],
                     "nested": {"collection": "steps", "id": "step_id", "field": "name",
                                "row_field": "step_name"},
                     "derived": ["reward_chain_id", "clan_type", "value_point"],
                     "keep": ["name", "description", "long_description", "popup_header",
                              "popup_instruction", "is_enabled", "date_start", "date_end",
                              "steps", "order", "image_url"]},
    "offer_chain": {"list": "/admin/offer_chain", "path": "/admin/offer_chain/id/{id}",
                    "no_write_while_active": "is_enabled",
                    "derived": ["number_of_steps"],
                    "id": "id", "fields": ["name", "description"],
                    "keep": ["id", "name", "description", "is_enabled", "is_always_visible",
                             "is_reset_on_completion", "date_start", "date_end", "steps",
                             "order", "recurrent_schedule"]},
}
# Attributes are nested (name + values[].value) and handled specially (singular paths).
ATTR = {"list": "/admin/attribute", "get": "/admin/attribute/{id}",
        "put_name": "/admin/attribute/{id}", "put_value": "/admin/attribute/{id}/value/{subid}"}

CATALOG_LOCALES = {"en", "ar", "bg", "my", "cn", "tw", "cs", "ph", "fr", "de", "he",
                   "id", "it", "ja", "km", "ko", "lo", "ne", "pl", "pt", "ro", "ru",
                   "es", "th", "tr", "vi"}

# The API accepts 2- or 5-letter codes on write but always answers in 2-letter, so
# everything here keys by 2-letter and 5-letter input is normalized down. Only the
# ONE canonical variant per language is valid: pt-BR -> pt, while pt-PT is not an
# Xsolla locale at all and 404s. See references/supported-languages.md.
LOCALE_5TO2 = {"en-US": "en", "ar-AE": "ar", "bg-BG": "bg", "my-MM": "my",
               "zh-CN": "cn", "zh-TW": "tw", "cs-CZ": "cs", "ph-PH": "ph",
               "fr-FR": "fr", "de-DE": "de", "he-IL": "he", "id-ID": "id",
               "it-IT": "it", "ja-JP": "ja", "km-KH": "km", "ko-KR": "ko",
               "lo-LA": "lo", "ne-NP": "ne", "pl-PL": "pl", "pt-BR": "pt",
               "ro-RO": "ro", "ru-RU": "ru", "es-ES": "es", "th-TH": "th",
               "tr-TR": "tr", "vi-VN": "vi"}

# Meta columns of the wide CSV, in canonical order. `context` is a translator hint
# and may be absent from a CSV a partner hands over; the rest address the string.
META_COLS = ["entity", "id", "subid", "field", "context"]
REQUIRED_COLS = ["entity", "id", "field"]

# Flags that take a value, so an unknown flag cannot silently swallow a positional.
VALUE_FLAGS = {"--env", "--entity", "--size", "--from", "--max-len", "--locale",
               "--source", "--pace", "--snapshot", "--on-conflict", "--backup"}
BARE_FLAGS = {"--missing", "--overwrite", "--dry", "--write", "--allow-field-loss",
              "--no-snapshot", "--no-verify", "--no-backup", "--allow-unverified"}


def _norm_locale(code):
    """Canonical 2-letter code, or None if it is not an Xsolla catalog locale."""
    c = (code or "").strip()
    if c in CATALOG_LOCALES:
        return c
    if c in LOCALE_5TO2:
        return LOCALE_5TO2[c]
    lower = c.lower()
    for k, v in LOCALE_5TO2.items():
        if k.lower() == lower:
            return v
    return lower if lower in CATALOG_LOCALES else None


def _unquote(v):
    """`KEY="value"` is ordinary .env style but the quotes are not part of the value —
    left in, they end up inside the Basic auth string and every call 401s."""
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v.strip()


ENV_HINT = ("set them in the environment, or pass --env PATH to a .env file holding "
            "bare values:\n  XSOLLA_PROJECT_ID=314067\n  XSOLLA_PROJECT_API_KEY=<key>")


def load_env(argv):
    env = dict(os.environ)
    if "--env" in argv:
        i = argv.index("--env")
        if i + 1 >= len(argv):
            sys.exit("--env needs a path to a .env file")
        path = argv[i + 1]
    else:
        path = os.environ.get("XSOLLA_ENV_FILE")
    if path:
        try:
            with open(path, encoding="utf-8-sig") as f:
                lines = f.readlines()
        except OSError as exc:
            sys.exit(f"cannot read env file {path}: {exc.strerror}. Check the path, or "
                     f"{ENV_HINT}")
        for line in lines:
            line = line.strip()
            if line.startswith("export "):
                line = line[len("export "):].strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), _unquote(v)
                # The file WINS over the ambient environment. It used to be
                # setdefault, which meant a stale `export XSOLLA_PROJECT_ID` left in
                # the caller's shell silently redirected every PUT to a different
                # catalog than the --env file named. Passing --env is a statement of
                # intent about which project gets written to, so it has to be the
                # value that survives. Report the override (key only, never a value).
                if k.startswith("XSOLLA_") and os.environ.get(k, v) != v:
                    print(f"  note: {k} from {path} overrides a different value "
                          f"already set in the environment")
                env[k] = v

    for k in ("XSOLLA_PROJECT_ID", "XSOLLA_PROJECT_API_KEY"):
        env[k] = _unquote(env.get(k) or "")
        if not env[k]:
            sys.exit(f"missing {k} — {ENV_HINT}")
    if "XSOLLA_MERCHANT_ID" in env:
        env["XSOLLA_MERCHANT_ID"] = _unquote(env["XSOLLA_MERCHANT_ID"])

    # Catch a malformed id here rather than as an opaque "HTTP 401" ten calls later.
    if not env["XSOLLA_PROJECT_ID"].isdigit():
        sys.exit(f"XSOLLA_PROJECT_ID must be numeric, got {env['XSOLLA_PROJECT_ID']!r} — "
                 f"strip quotes/whitespace from the value ({ENV_HINT})")
    return env


def _project_line(env):
    """The resolved project id, announced by every command that reads or writes a catalog.

    Nothing used to name it. The plan a user approves lists entity, id, field and locale
    but not which CATALOG it is aimed at, so a stale `export XSOLLA_PROJECT_ID` or the
    wrong `--env` could point an irreversible write at a different project with nothing
    on screen to catch it. Every other risk here has a visible guard — `!!` for field
    loss, `‼ BLOCKED` for active chains, a refusal for unknown locales — and this one
    had none. It prints the id only; the key is never echoed.
    """
    return f"project {env['XSOLLA_PROJECT_ID']}"


def _auths(env):
    pid, key = env["XSOLLA_PROJECT_ID"], env["XSOLLA_PROJECT_API_KEY"]
    auths = [base64.b64encode(f"{pid}:{key}".encode()).decode()]
    if env.get("XSOLLA_MERCHANT_ID"):
        auths.append(base64.b64encode(f"{env['XSOLLA_MERCHANT_ID']}:{key}".encode()).decode())
    return auths


# A hung admin call must not stall a bulk run, and one blip must not kill it.
REQUEST_TIMEOUT = 30                                  # seconds per attempt
RETRY_STATUSES = {429, 500, 502, 503, 504}            # transient; everything else is final
MAX_ATTEMPTS = 4


def _backoff(attempt, retry_after=None):
    """Seconds to wait: the server's Retry-After if it sent one, else 2^n capped."""
    if retry_after:
        try:
            return max(0.0, min(float(retry_after), 60.0))
        except (TypeError, ValueError):
            pass
    return min(2 ** attempt, 30)


def api(env, method, path, body=None, api_version="v2"):
    """-> (status, payload). Never raises on a network or HTTP problem: callers
    branch on the status, and a 500-item import must not die on one timeout.
    Status 0 means the request never completed (payload holds the reason)."""
    url = f"{API_BASE}/{api_version}/project/{env['XSOLLA_PROJECT_ID']}{path}"
    data = json.dumps(body).encode() if body is not None else None
    last = (0, {})
    for auth in _auths(env):
        for attempt in range(MAX_ATTEMPTS):
            req = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": f"Basic {auth}", "Content-Type": "application/json",
                "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                    raw = r.read().decode()
                    return r.status, (json.loads(raw) if raw else {})
            except urllib.error.HTTPError as e:
                # 200 chars used to cut off `errorMessageExtended`, which is where the API
                # says WHICH property it rejected — every 1102 had to be re-probed by hand.
                last = (e.code, e.read().decode(errors="replace")[:ERROR_BODY_CHARS])
                if e.code in RETRY_STATUSES and attempt < MAX_ATTEMPTS - 1:
                    wait = _backoff(attempt, e.headers.get("Retry-After"))
                    print(f"    .. HTTP {e.code}, retry {attempt + 2}/{MAX_ATTEMPTS} in {wait:.0f}s")
                    time.sleep(wait)
                    continue
                break
            except json.JSONDecodeError as e:
                return 0, f"response was not JSON: {e}"
            except (urllib.error.URLError, OSError) as e:
                reason = getattr(e, "reason", None) or e
                last = (0, f"network error: {reason}")
                if attempt < MAX_ATTEMPTS - 1:
                    wait = _backoff(attempt)
                    print(f"    .. {reason}, retry {attempt + 2}/{MAX_ATTEMPTS} in {wait:.0f}s")
                    time.sleep(wait)
                    continue
                break
        if last[0] not in (401, 403):
            return last
    return last


LIST_KEYS = ("items", "groups", "attributes", "promotions")


def _as_list(data):
    """Coerce a list payload out of whatever the endpoint answered -> list.

    Must tolerate a NON-dict: `api()` returns the error body (a string) as the payload
    on any HTTP or network failure, and `fetch_all` hands that straight here. Calling
    `.get()` on it raised AttributeError, so every failed list crashed with a traceback
    instead of being reported — which silently defeated the whole "a failed read is not
    an empty catalog" guarantee: `discover` could never print `(list failed HTTP n)` and
    `export` could never print INCOMPLETE, because neither was reached.
    """
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for k in LIST_KEYS:
        if isinstance(data.get(k), list):
            return data[k]
    # A shape we have not measured. Returning [] would read as "this entity has no
    # objects", which is the same silent-empty failure in a different coat, so say so.
    other = [k for k, v in data.items() if isinstance(v, list)]
    if other:
        print(f"  ! WARNING: list response uses an unrecognized key "
              f"({', '.join(sorted(other))}) — expected one of {', '.join(LIST_KEYS)}. "
              f"Treating it as empty; the listing is INCOMPLETE.")
    return []


# Totals the list endpoints expose, under different names per endpoint. Only
# virtual_items sends `has_more`; groups ignores limit/offset and answers with
# everything; attribute sends `total_count`. So the pagination loop below cannot
# be trusted to have seen every object on endpoint shapes we have not measured —
# comparing the count we got against the total the server reported turns a silent
# cap into a loud warning instead of a quietly half-translated catalog.
TOTAL_KEYS = ("total_items_count", "total_count", "total", "total_promotions_count")


def fetch_all(env, list_path, api_version="v2"):
    out, offset, total = [], 0, None
    while True:
        st, data = api(env, "GET", f"{list_path}?limit=50&offset={offset}", api_version=api_version)
        if st != 200:
            st, data = api(env, "GET", list_path, api_version=api_version)
            return _as_list(data), st
        if isinstance(data, dict):
            for k in TOTAL_KEYS:
                if isinstance(data.get(k), int):
                    total = data[k]
                    break
        batch = _as_list(data)
        out += batch
        if not (isinstance(data, dict) and data.get("has_more")):
            break
        offset += len(batch) or 50
    if total is not None and len(out) != total:
        print(f"  ! WARNING: {list_path} returned {len(out)} object(s) but the server "
              f"reports {total} — the listing is INCOMPLETE, so anything derived from "
              f"it (coverage, the exported CSV) covers only part of the catalog.")
    return out, 200


# --- discover / langs ----------------------------------------------------------

def _hydrate(env, e, objs):
    """Re-read each object when the list view omits what we need.

    A reward chain's `steps` only appear in the single-object GET, so exporting from the
    list would silently report the chain as fully covered while every step name is still
    in the source language. Attributes have the same shape and the same fix.
    """
    if not e.get("nested"):
        return objs
    out = []
    for o in objs:
        st, full = api(env, "GET", e["path"].format(id=o.get(e["id"])),
                       api_version=e.get("api", "v2"))
        out.append(full if st == 200 and isinstance(full, dict) else o)
    return out


def _coverage(objs, fields, nested=None):
    """-> (translatable strings, filled count per locale).

    Nested members count too — a reward chain's step names are real strings a player
    reads, and leaving them out would report a chain as fully covered while its steps
    are still English.
    """
    def bump(obj, filled):
        for loc, val in obj.items():
            if (val or "").strip():
                filled[loc] = filled.get(loc, 0) + 1

    total, filled = 0, {}
    for o in objs:
        for f in fields:
            if isinstance(o.get(f), dict):
                total += 1
                bump(o[f], filled)
        for member in (o.get(nested["collection"]) or []) if nested else []:
            if isinstance(member.get(nested["field"]), dict):
                total += 1
                bump(member[nested["field"]], filled)
    return total, filled


def discover(env):
    print(f"{_project_line(env)} — entities (what exists + coverage):")
    for name, e in ENTITIES.items():
        objs, st = fetch_all(env, e["list"], e.get("api", "v2"))
        if st != 200:
            print(f"  {name}: (list failed HTTP {st})"); continue
        if not objs:
            print(f"  {name}: 0 — skip (not offered)"); continue
        objs = _hydrate(env, e, objs)
        total, filled = _coverage(objs, e["fields"], e.get("nested"))
        cov = " · ".join(f"{loc} {filled[loc]}/{total}" for loc in sorted(filled)) or "no locales"
        print(f"  {name}: {len(objs)} object(s), {total} strings — {cov}")
    attrs, st = fetch_attributes(env)
    if st == 200 and attrs:
        names = len(attrs)
        vals = sum(len(a.get("values") or []) for a in attrs)
        filled = {}
        for a in attrs:
            for loc, v in (a.get("name") or {}).items():
                if (v or "").strip(): filled[loc] = filled.get(loc, 0) + 1
            for val in (a.get("values") or []):
                for loc, v in (val.get("value") or {}).items():
                    if (v or "").strip(): filled[loc] = filled.get(loc, 0) + 1
        total = names + vals
        cov = " · ".join(f"{loc} {filled[loc]}/{total}" for loc in sorted(filled)) or "no locales"
        print(f"  attribute: {names} attr(s) + {vals} value(s), {total} strings — {cov}")


def fetch_attributes(env):
    """The list endpoint omits values — GET each attribute to include them."""
    lst, st = fetch_all(env, ATTR["list"])
    if st != 200:
        return [], st
    full = []
    for a in lst:
        aid = a.get("external_id")
        st2, d = api(env, "GET", ATTR["get"].format(id=aid))
        full.append(d if st2 == 200 else a)
    return full, 200


def langs(env):
    objs, st = fetch_all(env, ENTITIES["items"]["list"])
    if st != 200:
        sys.exit(f"langs: the items list failed (HTTP {st}) — cannot report coverage. "
                 f"Check the credentials and project id.")
    total, filled = _coverage(objs, ENTITIES["items"]["fields"])
    print(f"translatable strings: {total} (across {len(objs)} items)")
    for loc in sorted(filled):
        print(f"  {loc}: {filled[loc]}/{total} ({round(100*filled[loc]/total) if total else 0}%)")


# --- export --------------------------------------------------------------------

def _row(entity, oid, subid, field, context, source, srcval, targets):
    r = {"entity": entity, "id": oid, "subid": subid, "field": field,
         "context": context, source: srcval}
    r.update(targets)
    return r


def export(env, out, locales, entities, source="en", only_missing=False):
    cols = ["entity", "id", "subid", "field", "context", source] + locales
    rows, counts, no_source = [], {}, 0
    # A list that failed must never be reported as an entity with nothing to
    # translate: "exported 0 rows" then reads exactly like a fully translated
    # catalog, and the agent goes on to tell the user there is no work to do.
    failures = []
    for ent in entities:
        if ent == "attribute":
            attrs, st = fetch_attributes(env)
            if st != 200:
                failures.append(f"attribute (HTTP {st})")
                print(f"  ! attribute: list failed HTTP {st} — NOT exported")
                continue
            counts["attribute"] = len(attrs)
            for a in attrs:
                aid = a.get("external_id")
                obj = a.get("name") or {}
                tg = {loc: obj.get(loc, "") for loc in locales}
                if not (only_missing and all(tg.values())):
                    rows.append(_row("attribute", aid, "", "name", f"attribute {aid} name", source, obj.get(source, ""), tg))
                for val in (a.get("values") or []):
                    vid = val.get("external_id"); vobj = val.get("value") or {}
                    tg = {loc: vobj.get(loc, "") for loc in locales}
                    if only_missing and all(tg.values()):
                        continue
                    rows.append(_row("attribute", aid, vid, "value", f"attribute {aid} value {vid}", source, vobj.get(source, ""), tg))
            continue
        e = ENTITIES.get(ent)
        if not e:
            failures.append(f"{ent} (unknown entity)")
            print(f"  ! unknown entity '{ent}' — NOT exported. Known: "
                  f"{', '.join(sorted(list(ENTITIES) + ['attribute']))}")
            continue
        objs, st = fetch_all(env, e["list"], e.get("api", "v2"))
        if st != 200:
            failures.append(f"{ent} (HTTP {st})")
            print(f"  ! {ent}: list failed HTTP {st} — NOT exported")
            continue
        counts[ent] = len(objs)
        objs = _hydrate(env, e, objs)
        for o in objs:
            oid = o.get(e["id"])
            for field in e["fields"]:
                obj = o.get(field)
                if not isinstance(obj, dict):
                    no_source += 1
                    continue
                tg = {loc: obj.get(loc, "") for loc in locales}
                if only_missing and all(tg.values()):
                    continue
                rows.append(_row(ent, oid, "", field, f"{ent} {oid} {field}", source, obj.get(source, ""), tg))
            # Nested members (a reward chain's steps) address by subid, exactly like an
            # attribute's values — same CSV shape, so batch/fill/merge/check need no
            # special case.
            n = e.get("nested")
            for member in (o.get(n["collection"]) or []) if n else []:
                nobj = member.get(n["field"])
                if not isinstance(nobj, dict):
                    continue
                sub = str(member.get(n["id"]))
                tg = {loc: nobj.get(loc, "") for loc in locales}
                if only_missing and all(tg.values()):
                    continue
                rows.append(_row(ent, oid, sub, n["row_field"],
                                 f"{ent} {oid} step {sub}", source, nobj.get(source, ""), tg))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    empty = sum(1 for r in rows for loc in locales if not r[loc])
    per = ", ".join(f"{k}:{v}" for k, v in counts.items()) or "none"
    print(f"exported {len(rows)} rows x {len(locales)} locale(s) from "
          f"{_project_line(env)} -> {out}")
    print(f"  entities: {per} | empty cells to translate: {empty}")
    if no_source:
        # Not an error — there is nothing to translate — but silence here reads as "this
        # entity has fewer fields than it does", which is how `long_description` looked
        # missing for a whole catalog.
        print(f"  {no_source} localizable field(s) produced no row because the source "
              f"text is empty (nothing to translate until someone fills them in).")
    if failures:
        print(f"  ! {len(failures)} entity list(s) FAILED: {', '.join(failures)}.")
        print(f"  -> {out} is INCOMPLETE. Do not read 0 rows as 'nothing to "
              f"translate' — fix the failure and re-export before importing.")
        return 1
    return 0


# --- batch / fill / check ------------------------------------------------------

def _valid_fields(entity):
    """Field names this entity can actually carry, or None if the entity is unknown.

    A row addressing something that does not exist — a promotion's `description`, a
    typo'd `nmae` — used to be dropped in silence: the loop iterates the entity's real
    fields, so anything else simply never matched. The translation was gone, `import`
    reported 0 changes and exited 0, and nothing said why. Cheap to detect, expensive to
    miss.
    """
    if entity == "attribute":
        return {"name", "value"}
    e = ENTITIES.get(entity)
    if not e:
        return None
    fields = set(e["fields"])
    if e.get("nested"):
        fields.add(e["nested"]["row_field"])
    return fields


def _row_problem(r):
    """-> None, or why this row addresses nothing.

    Checks the WHOLE address, because every part of it is consumed by an equality test
    somewhere and anything that does not match is dropped by a `continue`. `subid` was
    the gap: a non-empty one on an entity with no nested collection is excluded from the
    top-level pass by `not r.get("subid")` and then never looked at again, because
    `_merge_nested` returns early when the entity has no nested members — so the
    translation vanished with no message and the run exited 0.
    """
    ent = (r.get("entity") or "").strip()
    field = (r.get("field") or "").strip()
    oid = (r.get("id") or "").strip()
    subid = (r.get("subid") or "").strip()
    fields = _valid_fields(ent)
    if fields is None:
        return (f"unknown entity '{ent}' — known: "
                f"{', '.join(sorted(list(ENTITIES) + ['attribute']))}")
    if field not in fields:
        return (f"'{ent}' has no field '{field}' — it carries "
                f"{', '.join(sorted(fields))}")
    if not oid:
        return "empty id — nothing to address (the sku / external_id is required)"
    # Which fields address a nested member, and therefore REQUIRE a subid.
    if ent == "attribute":
        nested_field = "value"
    else:
        n = (ENTITIES.get(ent) or {}).get("nested")
        nested_field = n["row_field"] if n else None
    if field == nested_field and not subid:
        return (f"'{field}' addresses a nested member, so subid is required "
                f"(the step_id / value external_id)")
    if field != nested_field and subid:
        return (f"subid '{subid}' is set, but '{ent}'.'{field}' is a top-level field — "
                f"a row with a subid here matches nothing and would be dropped"
                + (f"; only '{nested_field}' takes a subid" if nested_field else ""))
    return None


def _conflicting_rows(rows, targets):
    """Addresses that appear twice with DIFFERENT non-empty values for one locale.

    Two rows for one string is not itself wrong (a hand-merged file, a re-export), but
    two different translations is a question only a human can settle — and picking one
    quietly is how a reviewed translation gets replaced by an unreviewed one.
    """
    seen, clashes = {}, []
    for r in rows:
        key = _key(r)
        for loc in targets:
            val = (r.get(loc) or "").strip()
            if not val:
                continue
            prev = seen.get((key, loc))
            if prev is None:
                seen[(key, loc)] = val
            elif prev != val:
                clashes.append(f"{'/'.join(key)}/{loc}: {prev!r} vs {val!r}")
    return clashes


def _read_csv(path, what="CSV"):
    """Open a user-supplied CSV -> (fieldnames, rows). A missing or unreadable file is an
    ordinary mistake (wrong path, wrong directory), so it gets a sentence, not a
    traceback. `utf-8-sig` because a CSV round-tripped through Excel arrives with a BOM,
    which would otherwise turn the first column name into '\ufeffentity'.
    """
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            names = reader.fieldnames
            rows = list(reader)
    except FileNotFoundError:
        sys.exit(f"{what} not found: {path}")
    except IsADirectoryError:
        sys.exit(f"{path} is a directory, not a {what}")
    except OSError as exc:
        sys.exit(f"cannot read {path}: {exc.strerror}")
    except UnicodeDecodeError as exc:
        sys.exit(f"{path} is not valid UTF-8 ({exc.reason}) — re-save it as UTF-8")

    # A repeated column name is data loss that happens INSIDE the parser: DictReader
    # keeps the last one, so `en,de,de` silently discards the first `de` before any
    # guard can compare the two. It cannot be detected downstream — by then the row is
    # already a dict with one `de` — so it has to be refused here.
    dupes = sorted({c for c in (names or []) if (names or []).count(c) > 1})
    if dupes:
        sys.exit(f"{path}: duplicate column name(s) {', '.join(repr(d) for d in dupes)}. "
                 f"Only the last column of each name survives parsing, so the others "
                 f"would be dropped silently — delete or rename the duplicates.")

    # A semicolon- or tab-delimited file parses as ONE column, and the caller then hears
    # "missing required column(s) entity, id, field" about columns that are all present.
    # Semicolon is the default CSV delimiter in European Excel, so this is the single
    # most likely thing a translator hands back.
    if names and len(names) == 1:
        for sep, label in ((";", "semicolon"), ("\t", "tab")):
            if sep in names[0]:
                sys.exit(f"{path} looks {label}-delimited, not comma-delimited: the whole "
                         f"header parsed as one column ({names[0][:60]!r}...). Re-save it "
                         f"as comma-separated UTF-8 (in Excel: Save As -> CSV UTF-8).")

    # Excel leaves trailing empty rows behind, and a blank line inside the file parses as
    # a row of empty strings. Left in, each one is reported as a string that could not be
    # found — a spurious failure and a non-zero exit on an otherwise good file.
    rows = [r for r in rows if any((v or "").strip() for v in r.values())]

    # Normalize the ADDRESS once, here, so validation and consumption cannot disagree.
    # They did: `_row_problem` stripped `entity`/`field` while the plan loop matched
    # them raw, so `field=" name"` passed `check` clean and was then dropped at import
    # with no message at all. A short row also yields None rather than "", which made
    # two spellings of the same empty `subid`.
    for r in rows:
        for c in META_COLS:
            if c in r:
                r[c] = (r[c] or "").strip()
    return names, rows


def _source_column_problem(src, targets):
    """Why the source column looks misidentified, or None.

    Which column is the source is positional — the first language column — and nothing
    in the schema records it, so a spreadsheet round-trip that reorders the columns
    inverts the convention: the source becomes a target and a finished locale is never
    imported. A non-English source while `en` sits further right is almost always a
    reordered file rather than a catalog authored in German, and nothing in the file can
    tell the two apart — so this has to stop the run and be answered by a human
    (`--source`), not printed and stepped over. It was printed and stepped over once,
    which let a reordered file pass `check` clean.
    """
    if _norm_locale(src) == "en":
        return None
    if any(_norm_locale(t) == "en" for t in targets):
        return (f"'{src}' is being read as the SOURCE column because it comes first, "
                f"and 'en' as a target — so every {src} translation in this file would "
                f"be ignored. If the columns were reordered, put the source column "
                f"first; if the catalog really is authored in {src}, pass "
                f"--source {src} to say so.")
    # No `en` column at all. The first language column is still being taken as the
    # source, so its contents are read as reference text and never written — and with
    # no `en` to compare against, the check above cannot see it. That is the shape of a
    # PARTNER file: a translator returning `de,fr` had German silently swallowed as
    # "the source" while the run reported success. `merge` was taught to treat every
    # language column in such a file as a target; `check` and `import` were not, so
    # they kept losing the first locale with a clean exit code.
    return (f"'{src}' is being read as the SOURCE column because it comes first, and "
            f"there is no 'en' column to cross-check against — so every {src} value "
            f"here is treated as reference text and will NOT be imported. A file with "
            f"no source column is usually a partner's: load it with "
            f"`merge <working.csv> --from <this file>`, which treats every language "
            f"column as a target. If this catalog really is authored in {src}, pass "
            f"--source {src}.")


def _cols(fieldnames, path="the CSV", announce=False, source=None):
    """(source, targets) — by column NAME, so a partner CSV with `context` missing,
    extra columns, or a different order still works. Fails with an explanation
    rather than an IndexError/ValueError from inside the parser."""
    if not fieldnames:
        sys.exit(f"{path}: no header row — expected columns "
                 f"{', '.join(META_COLS)}, <source>, <locale...>")
    names = [(c or "").strip() for c in fieldnames]
    missing = [c for c in REQUIRED_COLS if c not in names]
    if missing:
        sys.exit(f"{path}: missing required column(s) {', '.join(missing)}. "
                 f"Expected {', '.join(META_COLS)}, <source>, <locale...> — got "
                 f"{', '.join(names) or '(empty)'}. If this is a partner's file, "
                 f"load it with `merge` instead of using it directly.")
    rest = [c for c in names if c not in META_COLS]
    if not rest:
        sys.exit(f"{path}: no source or locale columns after {', '.join(META_COLS)} — "
                 f"nothing to translate.")
    if len(rest) == 1:
        sys.exit(f"{path}: only one language column ('{rest[0]}') — a source column "
                 f"plus at least one target locale is required.")
    src, targets = rest[0], rest[1:]
    # An explicit --source makes the positional convention non-positional, which is the
    # actual repair for a reordered file: name the source and the column order stops
    # mattering. Callers gate on _source_column_problem() when it is absent.
    if source:
        want = _norm_locale(source) or source.strip()
        if want not in rest:
            sys.exit(f"{path}: --source {source} is not a language column in this file "
                     f"(language columns: {', '.join(rest)}).")
        src, targets = want, [c for c in rest if c != want]
    if announce:
        print(f"  source column: '{src}' · target locale(s): {', '.join(targets)}")
    return src, targets


# A column name that is TRYING to be a locale: `fr`, `fra`, `fr-CA`, `pt_PT`, `zh-Hans`.
# Anything of this shape that does not resolve is refused rather than skipped, because
# skipping it would silently discard a translator's work. Anything NOT of this shape
# (`translator`, `status`, `notes`, `reviewed by`) cannot be a locale attempt, so it is
# ignored — but named, never silently.
LOCALE_SHAPE = re.compile(r"^[A-Za-z]{2,3}([-_][A-Za-z]{2,4})?$")


def _partner_cols(fieldnames, path):
    """Language columns of a PARTNER file — every one of them is a target.

    Never reuse the working file's rule here. That one reads the first language column
    as the source and the rest as targets, which is right for a file we produced and
    wrong for one a translator hands back: a partner who returns `de,ru` and no English
    would have had German silently swallowed as "the source" and dropped, while the run
    reported success. Measured, not hypothetical.
    """
    if not fieldnames:
        sys.exit(f"{path}: no header row")
    names = [(c or "").strip() for c in fieldnames]
    missing = [c for c in REQUIRED_COLS if c not in names]
    if missing:
        sys.exit(f"{path}: missing required column(s) {', '.join(missing)} — a partner "
                 f"file still has to say which string each row is.")
    langs = [c for c in names if c not in META_COLS]
    if not langs:
        sys.exit(f"{path}: no language columns after {', '.join(META_COLS)} — "
                 f"nothing to merge.")
    return langs


def _key(r):
    return (r["entity"], r["id"], r.get("subid", ""), r["field"])


def batch(path, locale, size):
    if not locale:
        sys.exit("batch: --locale required")
    fieldnames, rows = _read_csv(path)
    src, _ = _cols(fieldnames, path)
    pending = [{"entity": r["entity"], "id": r["id"], "subid": r.get("subid", ""),
                "field": r["field"], "context": r.get("context", ""), "source": r.get(src, "")}
               for r in rows if not (r.get(locale) or "").strip()]
    print(json.dumps({"locale": locale, "remaining": len(pending), "batch": pending[:size]},
                     ensure_ascii=False, indent=2))


# The model writes the JSON that `fill` consumes, so accept the shapes a model
# actually produces and explain the ones that cannot be salvaged. Never crash: a
# traceback mid-loop costs the whole batch of translation work.
VALUE_KEYS = ("translation", "value", "text", "target", "translated")


def _parse_fill(raw, locale):
    """-> (entries, problems). Tolerates a ```json fence and a wrapper object."""
    txt = (raw or "").strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt)
        txt = re.sub(r"\n?```\s*$", "", txt).strip()
    if not txt:
        sys.exit(f"fill: no input on stdin/--from. Expected a JSON list of "
                 f"{{entity, id, subid, field, translation}} for locale '{locale}'.")
    try:
        data = json.loads(txt)
    except json.JSONDecodeError as exc:
        sys.exit(f"fill: input is not valid JSON — {exc}\n"
                 f"  near: {txt[max(0, exc.pos - 40):exc.pos + 40]!r}\n"
                 f"  expected a JSON list of {{entity, id, subid, field, translation}}.")
    if isinstance(data, dict):
        for k in ("batch", "translations", "items", "rows", "data"):
            if isinstance(data.get(k), list):
                data = data[k]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        sys.exit(f"fill: expected a JSON list, got {type(data).__name__}.")

    entries, problems = {}, []
    for i, t in enumerate(data):
        if not isinstance(t, dict):
            problems.append(f"entry #{i}: expected an object, got {type(t).__name__}")
            continue
        val = next((t[k] for k in VALUE_KEYS if isinstance(t.get(k), str) and t[k].strip()), None)
        if val is None:
            problems.append(f"entry #{i}: no translation text — keys present: "
                            f"{sorted(t)}; expected one of {list(VALUE_KEYS)}")
            continue
        missing = [k for k in ("entity", "id", "field") if not str(t.get(k) or "").strip()]
        if missing:
            problems.append(f"entry #{i} ({val[:24]!r}): missing {', '.join(missing)}")
            continue
        key = (str(t["entity"]).strip(), str(t["id"]).strip(),
               str(t.get("subid") or "").strip(), str(t["field"]).strip())
        # Two entries for one cell used to collapse into the dict, last one winning,
        # with nothing said. This input is written by a model, so it is the likeliest
        # place for a contradiction — and `check` and `merge` both refuse to pick for
        # you. An identical repeat carries no information, so it dedupes quietly; two
        # DIFFERENT values are a question, so drop both and name them.
        if key in entries and entries[key] != val:
            problems.append(f"{'/'.join(key)}: two different translations in one payload "
                            f"({entries[key]!r} and {val!r}) — neither was used; "
                            f"re-send the one you want")
            entries[key] = None
            continue
        if entries.get(key, "") is None:
            continue                      # already disputed; ignore further repeats
        entries[key] = val
    return {k: v for k, v in entries.items() if v is not None}, problems


def fill(path, locale, source_arg):
    if not locale:
        sys.exit("fill: --locale required")
    if source_arg in (None, "-", ""):
        raw = sys.stdin.read()
    else:
        try:
            with open(source_arg, encoding="utf-8") as f:
                raw = f.read()
        except OSError as exc:
            sys.exit(f"fill: cannot read --from {source_arg}: {exc.strerror}")
    entries, problems = _parse_fill(raw, locale)

    cols, rows = _read_csv(path)
    _cols(cols, path)
    if locale not in [(c or "").strip() for c in cols]:
        canon = _norm_locale(locale)
        hint = (f" Did you mean '{canon}'? The CSV columns are 2-letter codes."
                if canon and canon in cols else
                f" Columns: {', '.join(c for c in cols if c not in META_COLS)}.")
        sys.exit(f"fill: no '{locale}' column in {path}.{hint}")

    used, n = set(), 0
    for r in rows:
        k = _key(r)
        v = entries.get(k)
        if v and v.strip():
            r[locale] = v.strip(); used.add(k); n += 1
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

    unmatched = [k for k in entries if k not in used]
    print(f"filled {n} cell(s) for '{locale}' in {path}")
    for pr in problems:
        print(f"  ! unusable {pr}")
    if unmatched:
        print(f"  ! {len(unmatched)} translation(s) matched NO row and were DISCARDED "
              f"(address must equal the batch's entity/id/subid/field exactly):")
        for k in unmatched[:10]:
            print(f"      entity={k[0]} id={k[1]} subid={k[2]!r} field={k[3]}")
        if len(unmatched) > 10:
            print(f"      ... and {len(unmatched) - 10} more")
    if problems or unmatched:
        print(f"  -> the {n} cell(s) above ARE saved; re-send only the discarded ones "
              f"(re-run `batch --locale {locale}` to get their exact addresses).")
        return 1
    return 0


def merge(path, from_path, overwrite=False):
    """Load a partner-supplied CSV into the working CSV, strictly by address.

    SKILL.md contract: merge by id; ids not present locally are NOT added, they are
    reported back; locale codes are normalized 5->2; nothing is guessed.
    """
    # Read it through the SAME hardened reader as every other CSV. This used to be a
    # bare DictReader, which meant the one file that arrives from outside — written by
    # a translator, on their machine, with their tooling — was the only one missing
    # every guard: a Latin-1 file raised a raw UnicodeDecodeError (only OSError was
    # caught), a duplicate column silently kept the last value, a semicolon-delimited
    # file got a misleading "missing required column(s)", and Excel's trailing blank
    # rows were reported as strings that could not be found.
    inc_cols, inc = _read_csv(from_path, what="partner CSV")
    if not inc:
        sys.exit(f"merge: {from_path} has no data rows")
    inc_targets = _partner_cols(inc_cols, from_path)

    # Map each incoming language column onto a canonical catalog locale.
    mapping, unknown = {}, []
    for col in inc_targets:
        canon = _norm_locale(col)
        if canon:
            mapping[col] = canon
        else:
            unknown.append(col)
    # Split what failed to resolve: a locale-SHAPED name is a locale someone got wrong,
    # and dropping it would discard their translations — that stays fatal. A name that
    # cannot be a locale at all is translator metadata (`translator`, `status`, `notes`),
    # which real TMS and XLIFF exports add as a matter of course; rejecting the whole
    # file over it made the publisher path brittle. Ignore those, but say which.
    bad_locale = [u for u in unknown if LOCALE_SHAPE.match(u)]
    metadata = [u for u in unknown if u not in bad_locale]
    if bad_locale:
        sys.exit(f"merge: {from_path} has language column(s) that are not Xsolla catalog "
                 f"locales: {', '.join(repr(u) for u in bad_locale)}. Rename them to a "
                 f"canonical code (see references/supported-languages.md) or drop them — "
                 f"guessing would write a translation into the wrong language.")
    if metadata:
        print(f"  ignoring non-locale column(s): {', '.join(sorted(metadata))} "
              f"(not language codes, so nothing in them is imported)")
    if not mapping:
        sys.exit(f"merge: {from_path} has no locale columns to merge — only "
                 f"{', '.join(sorted(metadata))}.")
    for clash in _conflicting_rows(inc, list(mapping)):
        print(f"  ! {from_path} gives two different translations for one cell, the "
              f"first is used — {clash}")
    renamed = {c: l for c, l in mapping.items() if c != l}
    if renamed:
        print("  normalized locale column(s): "
              + ", ".join(f"{c} -> {l}" for c, l in sorted(renamed.items())))

    cols, rows = _read_csv(path)
    local_src, _ = _cols(cols, path)
    if local_src in mapping.values():
        dropped = [c for c, l in mapping.items() if l == local_src]
        mapping = {c: l for c, l in mapping.items() if l != local_src}
        print(f"  ignoring column(s) {', '.join(dropped)}: '{local_src}' is the source "
              f"column of {path}, not a translation target")
        if not mapping:
            sys.exit(f"merge: {from_path} carries only the source language "
                     f"('{local_src}') — no translations to merge.")
    local = {_key(r): r for r in rows}

    # Locales the partner filled that the working CSV has no column for.
    new_cols = [l for l in sorted(set(mapping.values())) if l not in cols]
    cols = list(cols) + new_cols
    if new_cols:
        print(f"  added column(s) for locale(s) not yet in {path}: {', '.join(new_cols)}")
        for r in rows:
            for l in new_cols:
                r.setdefault(l, "")

    filled = kept = 0
    not_found, blank = [], 0
    for r in inc:
        key = (str(r.get("entity") or "").strip(), str(r.get("id") or "").strip(),
               str(r.get("subid") or "").strip(), str(r.get("field") or "").strip())
        target = local.get(key)
        if target is None:
            not_found.append(key)
            continue
        for col, loc in mapping.items():
            val = (r.get(col) or "").strip()
            if not val:
                blank += 1
                continue
            if (target.get(loc) or "").strip() and not overwrite:
                kept += 1
                continue
            target[loc] = val; filled += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)

    print(f"merged {from_path} -> {path}: {filled} cell(s) filled, {kept} existing kept "
          f"({'overwrite on' if overwrite else 'fill-only'}), {blank} blank source cell(s) skipped")
    if not_found:
        print(f"  ! {len(not_found)} row(s) NOT loaded — no such string in {path} "
              f"(reported, not added):")
        for k in not_found[:10]:
            # `_row_problem` knows the registry, so an unknown entity or a field the
            # entity does not carry gets named instead of being blamed on the id. A
            # title-cased `Items`/`Name` from a translator's tooling used to come back
            # as "this id does not exist", which points at the wrong thing.
            why = _row_problem({"entity": k[0], "id": k[1], "subid": k[2], "field": k[3]})
            print(f"      entity={k[0]} id={k[1]} subid={k[2]!r} field={k[3]}"
                  + (f"\n        -> {why}" if why else ""))
        if len(not_found) > 10:
            print(f"      ... and {len(not_found) - 10} more")
        print("  -> these ids do not exist in the exported catalog. Check the id/field "
              "spelling, or re-run `export` if the catalog changed.")
    return 1 if not_found else 0


PRINTF = re.compile(r"%(?:\d+\$)?[sdifgu]|%%")


def _placeholders(text):
    """Variable identities in a string -> (brace-arg names, printf tokens).

    Brace groups are matched with a nesting counter and reduced to the ARGUMENT
    NAME, so an ICU plural survives translation: `{n, plural, one {# day} other
    {# days}}` yields `n` in every language, even though the sub-messages differ
    in count and wording between languages. A flat regex could not do this — it
    stopped at the first `}` and compared sub-message text, so every correct ICU
    translation looked like a placeholder mismatch.
    """
    names, i, n = set(), 0, len(text or "")
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth, j = 0, i
        while j < n:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if depth != 0:                       # unbalanced brace: nothing to compare
            break
        inner = text[i + 1:j].strip()
        if inner.startswith("{") and inner.endswith("}"):
            inner = inner[1:-1].strip()      # {{name}} handlebars form
        arg = inner.split(",", 1)[0].strip()
        if arg:
            names.add(arg)
        i = j + 1
    return names, sorted(PRINTF.findall(text or ""))


TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9]*)[^>]*>")
URL = re.compile(r"https?://[^\s<>\"')\]]+")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# Replacement char plus C0 controls other than tab/newline: what a mangled
# encoding round-trip actually leaves behind in a CSV cell.
BAD_CHARS = re.compile(r"[\ufffd\x00-\x08\x0b\x0c\x0e-\x1f]")

# Ratio checks are meaningless on short strings: `Gems` -> `Edelsteine` is +150%
# and perfectly correct, while a long description moves by a few percent. So the
# ratio only applies above this length, and below it only exact-copy is checked.
RATIO_MIN_CHARS = 20
RATIO_LONG = 3.0     # target this many times the source = the model added something
RATIO_SHORT = 0.4    # this much shorter = part of the string was dropped


def _markup(text):
    """Tag multiset (name, is_closing) — markup that must survive translation."""
    out = {}
    for closing, name in TAG.findall(text or ""):
        k = (name.lower(), bool(closing))
        out[k] = out.get(k, 0) + 1
    return out


def _links(text):
    """URLs, from bare occurrences and from markdown link targets."""
    found = set(URL.findall(text or "")) | set(MD_LINK.findall(text or ""))
    return {u.rstrip(".,;:!?") for u in found}


def _parse_max_len(arg):
    """`40` -> every field; `name=30,description=200` -> per field.

    One global number is useless in practice: it never fires on the short `name`s
    that actually break a layout, and fires constantly on descriptions that are fine.
    """
    arg = (arg or "").strip()
    if not arg:
        return {}
    # A limit below 1 is never what anyone means, and both ends of the range failed
    # quietly: a negative one is truthy, so `--max-len -5` warned on every single cell,
    # while `--max-len 0` is falsy and silently disabled the check it was asked to run.
    def _limit(n, part):
        try:
            v = int(n)
        except ValueError:
            sys.exit(f"--max-len: '{part}' is not {'field=N' if '=' in part else 'a number or a field=N list'}")
        if v < 1:
            sys.exit(f"--max-len: '{part}' is not a usable limit — it must be 1 or more "
                     f"(a negative limit flags every cell, and 0 silently disables the "
                     f"check; omit --max-len to skip it).")
        return v

    if "=" not in arg:
        return {"*": _limit(arg, arg)}
    out = {}
    for part in arg.split(","):
        part = part.strip()
        if not part:
            continue
        f, _, n = part.partition("=")
        f = f.strip()
        if not f:
            sys.exit(f"--max-len: '{part}' has no field name before '=' — use "
                     f"field=N (or a bare number for every field).")
        out[f] = _limit(n, part)
    return out


def _hard_value_issues(rows, src, targets):
    """The deterministic value checks that mean BREAKAGE, not just style -> list.

    `import` does not require `check` to have been run, and it deliberately only
    re-validates what is catastrophic (an unknown locale drops the whole PUT). But a
    renamed placeholder or an unbalanced tag breaks the storefront, and a plan that
    prints such a value without comment invites a "yes" to it. So the same checks run
    here too, as a visible warning on the plan rather than a block: import guards data,
    `check` judges content, and the human approving deserves to see both.
    Soft signals (echo, length, ratio) are left out — they are judgement, not breakage.
    """
    out = []
    for r in rows:
        srcval = r.get(src, "") or ""
        s_names, s_printf = _placeholders(srcval)
        s_tags, s_links = _markup(srcval), _links(srcval)
        for loc in targets:
            val = (r.get(loc) or "").strip()
            if not val:
                continue
            where = f"{r.get('entity')}/{r.get('id')}/{r.get('subid') or ''}/{r.get('field')}/{loc}"
            names, printf = _placeholders(val)
            if names != s_names or printf != s_printf:
                out.append(f"{where}: placeholder mismatch")
            if _markup(val) != s_tags:
                out.append(f"{where}: markup mismatch")
            if _links(val) != s_links:
                out.append(f"{where}: URL mismatch")
            if BAD_CHARS.findall(val):
                out.append(f"{where}: broken encoding")
    return out


def check(path, max_len=0, source=None):
    limits = max_len if isinstance(max_len, dict) else _parse_max_len(str(max_len or ""))
    cols, rows = _read_csv(path)
    src, targets = _cols(cols, path, announce=True, source=source)
    issues, soft, empty = [], [], 0
    # Blocking, and counted with everything else: a `!` line that left the exit code at
    # 0 contradicted this skill's own contract ("`!` is blocking") and let the reordered
    # file it was written to catch sail through QA.
    if not source:
        prob = _source_column_problem(src, targets)
        if prob:
            issues.append(prob)
    for loc in targets:
        if loc in CATALOG_LOCALES:
            continue
        canon = _norm_locale(loc)
        if canon:
            soft.append(f"column '{loc}': 5-letter code — rename to '{canon}' "
                        f"(responses are always 2-letter; `merge` normalizes automatically)")
        else:
            issues.append(f"column '{loc}': not a catalog locale — remove or fix "
                          f"(an unknown locale 404s and drops the whole PUT on import)")
    for r in rows:
        prob = _row_problem(r)
        if prob:
            issues.append(f"row {r.get('entity')}/{r.get('id')}/{r.get('field')}: {prob}")
    for clash in _conflicting_rows(rows, targets):
        issues.append(f"two different translations for one cell — {clash}")
    for r in rows:
        srcval = r.get(src, "") or ""
        # Every check below compares the target against the source, so an empty source
        # with a filled target runs NONE of them while `check` still reports clean.
        # Say so rather than imply the cell was verified. (`export` never emits such a
        # row — it can only arrive by hand-editing or from a partner file.)
        if not srcval.strip() and any((r.get(loc) or "").strip() for loc in targets):
            soft.append(f"{r['entity']}/{r['id']}/{r.get('subid','')}/{r['field']}: "
                        f"translated but the '{src}' source cell is empty — "
                        f"placeholder, markup, URL and length checks cannot run on it")
        src_names, src_printf = _placeholders(srcval)
        src_tags, src_links = _markup(srcval), _links(srcval)
        for loc in targets:
            val = (r.get(loc) or "").strip()
            where = f"{r['entity']}/{r['id']}/{r.get('subid','')}/{r['field']}/{loc}"
            if not val:
                empty += 1; continue

            names, printf = _placeholders(val)
            if names != src_names or printf != src_printf:
                issues.append(f"{where}: placeholder mismatch "
                              f"src={sorted(src_names) + src_printf} got={sorted(names) + printf}")

            # Markup: a dropped </b> or an invented <br> breaks the storefront, not
            # just the string, and neither is visible in a diff of the words.
            tags = _markup(val)
            if tags != src_tags:
                issues.append(f"{where}: markup mismatch src={sorted(src_tags)} got={sorted(tags)}")
            for (nm, closing), n in tags.items():
                if not closing and tags.get((nm, True), 0) not in (0, n):
                    issues.append(f"{where}: unbalanced <{nm}> markup")

            # URLs: translating the inside of a link is a silent, common model error.
            links = _links(val)
            if links != src_links:
                issues.append(f"{where}: URL mismatch src={sorted(src_links)} got={sorted(links)}")

            bad = BAD_CHARS.findall(val)
            if bad:
                issues.append(f"{where}: broken encoding — {len(bad)} replacement/control "
                              f"character(s) in the cell")

            # A target byte-identical to the source is usually an echoed English
            # string. Some terms legitimately match, so warn rather than block.
            if val == srcval.strip() and re.search(r"[^\W\d_]", val):
                soft.append(f"{where}: identical to the {src} source — untranslated?")

            lim = limits.get(r["field"], limits.get("*"))
            if lim and len(val) > lim:
                soft.append(f"{where}: length {len(val)} > {lim} for field '{r['field']}'")

            if len(srcval) >= RATIO_MIN_CHARS:
                ratio = len(val) / len(srcval)
                if ratio >= RATIO_LONG:
                    soft.append(f"{where}: {ratio:.1f}x longer than source — added text?")
                elif ratio <= RATIO_SHORT:
                    soft.append(f"{where}: {ratio:.1f}x the source length — dropped text?")
    for i in issues:
        print("  ! " + i)
    for w in soft:
        print("  ~ " + w)
    print(f"{len(issues)} blocking issue(s), {len(soft)} warning(s), "
          f"{empty} empty cell(s), {len(rows)} rows")
    print("note: glossary compliance and register are NOT checked here — they are not "
          "deterministic. See references/qa.md for the agent's semantic pass.")
    return 1 if issues else 0


# --- import --------------------------------------------------------------------

# Server-derived / read-only fields the admin GET returns but a PUT must not carry
# back. Everything NOT listed here is passed through, because the catalog PUT
# REPLACES the object: an allowlist silently wipes every field it forgot about
# (verified on a live item — image_url, groups, inventory_options were all lost).
DERIVED = {"item_id", "type", "regional_prices", "items_count", "project_id",
           "created_at", "updated_at", "can_be_bought", "is_deleted", "promotions",
           # read-only capability flag, sibling of can_be_bought. Sending it back
           # made every value_points PUT fail with errorCode 1102 (measured).
           "can_delete"}

# `limits.recurrent_schedule` comes back carrying the server's COMPUTED schedule
# state — the next reset timestamp and the displayable reset dates. Those are
# derived, and echoing them back on a PUT is rejected with errorCode 1102, which
# took out every item with a recurring limit (a daily/weekly gift). Keep only the
# keys that actually define the schedule. Verified: the 2 failing items on 314067
# were exactly the 2 with a non-null recurrent_schedule; the other 8 had none.
SCHEDULE_KEEP = {"interval_type", "day_of_month", "day_of_week", "time"}


def _shape_limits(limits):
    """Reduce a `limits` read form to what the write schema accepts.

    The schedule is a oneOf over interval types (hourly/daily/weekly/monthly) that
    "does not allow additional properties", so every key the read form carries but
    the chosen branch does not define has to go: the computed state
    (reset_next_date, displayable_reset_*) AND the null placeholders for the other
    branches' keys (`day_of_month: null` on a weekly schedule made the PUT fail
    with "NULL value found, but an integer is required").
    """
    out = {k: v for k, v in limits.items() if k != "recurrent_schedule"}
    rs = limits.get("recurrent_schedule")
    if isinstance(rs, dict):
        out["recurrent_schedule"] = {
            scope: ({k: v for k, v in cfg.items()
                     if k in SCHEDULE_KEEP and v is not None}
                    if isinstance(cfg, dict) else cfg)
            for scope, cfg in rs.items()}
    elif "recurrent_schedule" in limits:
        out["recurrent_schedule"] = rs
    return out


def _shape(body, e):
    """Normalize enriched GET forms into the minimal shapes PUT accepts."""
    if isinstance(body.get("content"), list):
        body["content"] = [{"sku": c.get("sku"), "quantity": c.get("quantity", 1)} for c in body["content"]]
    # game keys: per-DRM unit_items in minimal form, prices as numbers.
    if isinstance(body.get("unit_items"), list):
        body["unit_items"] = [{"sku": u.get("sku"), "name": u.get("name"), "drm_sku": u.get("drm_sku"),
                               "prices": [{**p, "amount": float(p["amount"])} if "amount" in p
                                          else p for p in (u.get("prices") or [])],
                               "is_enabled": u.get("is_enabled", True),
                               "is_show_in_store": u.get("is_show_in_store", True)}
                              for u in body["unit_items"]]
    # group membership comes back enriched (id + localized name); PUT takes ids.
    if isinstance(body.get("groups"), list):
        body["groups"] = [g.get("external_id") if isinstance(g, dict) else g for g in body["groups"]]
    if isinstance(body.get("prices"), list):
        body["prices"] = [{**p, "amount": float(p["amount"])} if "amount" in p else p for p in body["prices"]]
    if isinstance(body.get("limits"), dict):
        body["limits"] = _shape_limits(body["limits"])
    # ...unless this entity's write schema rejects it: `derived` wins over the default,
    # or the shaping step silently re-adds exactly what the caller just stripped.
    # A reward-chain step is rejected without its `step_id`, and its `reward` comes back
    # enriched with the full item objects that the write schema will not take.
    # NOTE: this is deliberately an ALLOWLIST, which the pass-through rule forbids
    # everywhere else — the enriched read form is rejected outright, so there is no
    # pass-through shape to send. It carries the allowlist's cost: a step field Xsolla
    # adds later is dropped silently. Re-measure a step's write form when the API
    # changes, and prefer widening this list to widening the exception.
    if e.get("nested", {}).get("collection") == "steps" and isinstance(body.get("steps"), list):
        body["steps"] = [{"step_id": st.get("step_id"), "name": st.get("name"),
                          "price": st.get("price"),
                          "reward": [{"sku": r.get("sku"), "quantity": r.get("quantity", 1)}
                                     for r in (st.get("reward") or [])]}
                         for st in body["steps"]]
    if ("is_enabled" in e["keep"] and "is_enabled" not in e.get("derived", ())
            and "is_enabled" not in body):
        if e.get("no_write_while_active"):
            # Never invent the flag that gates a live mechanic. For a chain, defaulting
            # it to True would ENABLE one whose read omitted the field — putting a
            # mechanic in front of players, which is precisely the action this skill
            # promises it never takes. If a schema demands the key, let it say so in a
            # 422 naming `is_enabled`; a loud failure beats a silent enable.
            pass
        else:
            body.setdefault("is_enabled", True)
    return body


def _put_body(e, obj, merged, allow_field_loss=False):
    """Full state for a REPLACE PUT. Pass-through by default; the narrow `keep`
    allowlist is opt-in via --allow-field-loss (it drops untracked fields)."""
    # Some fields are server-derived for ONE entity only, so they cannot live in the
    # global DERIVED set — each entity lists its own in "derived". Measured, per entity,
    # from the 1102 the write returns; never guessed.
    extra = set(e.get("derived", ()))
    # Some schemas reject an EMPTY collection where they accept a populated one — a
    # game with `periods: []` is refused ("Matched a schema which it should not") while
    # the identical field on an item is fine. Drop the key only when it is empty, never
    # unconditionally: on a REPLACE write, dropping a populated one would delete it.
    extra |= {k for k in e.get("drop_if_empty", ())
              if isinstance(obj.get(k), (list, dict)) and not obj.get(k)}
    src = (e["keep"] if allow_field_loss
           else [k for k in obj if k not in DERIVED and k not in extra])
    body = {k: obj[k] for k in src if k in obj and obj[k] is not None}
    # A null value is normally omitted (the API rejects nulls on plenty of fields),
    # but some properties are required even when null — omitting them fails the
    # write outright. Those are listed per entity, from measurement, not guesswork.
    for k in e.get("always_send", ()):
        if k in obj and k not in body:
            body[k] = obj[k]
    body.update(merged)
    return _shape(body, e)


def _dropped(e, obj, allow_field_loss):
    """Fields present on GET that this write would NOT carry back — i.e. wiped."""
    kept = set(e["keep"]) if allow_field_loss else {k for k in obj if k not in DERIVED}
    return sorted(k for k in obj if k not in kept and k not in DERIVED and obj[k] not in (None, [], {}))


def _merge_loc(cur, rows, locales, field, overwrite):
    obj = dict(cur or {})
    planned = []
    for r in rows:
        for loc in locales:
            val = (r.get(loc) or "").strip()
            if not val or obj.get(loc) == val:
                continue
            if obj.get(loc) and not overwrite:
                continue
            obj[loc] = val; planned.append(f"{field}.{loc}='{val[:24]}'")
    return obj, planned


OK_STATUS = (200, 201, 204)


def plan_attribute(env, aid, rows, locales, overwrite):
    """-> (puts, planned, failures, snaps). Plans the nested name/value PUTs, writes none.

    Attributes are planned in the same pass as flat entities so the snapshot can
    be taken once, covering the whole run, before anything is written.

    `snaps` are RAW PUT records: an attribute has no single object whose body a
    restore could rebuild — name and each value are separate endpoints — so what
    is captured is the exact body that puts the pre-write state back, one per
    planned write. Same endpoint and same body shape as the write itself, so the
    rollback path is exercised by every attribute write test.
    """
    st, attr = api(env, "GET", ATTR["get"].format(id=aid))
    if st != 200:
        print(f"  ! skip attribute/{aid}: GET {st}")
        # 4-tuple: the caller unpacks (puts, planned, failures, snaps). Returning three
        # raised a ValueError from the unpack, so an attribute whose GET failed crashed
        # the run instead of being reported as one skipped object.
        return [], 0, 1, []
    puts, planned_n, snaps = [], 0, []

    name_rows = [r for r in rows if r["field"] == "name" and not r.get("subid")]
    if name_rows:
        obj, planned = _merge_loc(attr.get("name"), name_rows, locales, "name", overwrite)
        if planned:
            planned_n += len(planned)
            print(f"  attribute/{aid} name: {', '.join(planned)}")
            puts.append((f"attribute/{aid} name", ATTR["put_name"].format(id=aid),
                         {"external_id": aid, "name": obj}, len(planned)))
            snaps.append({"entity": "attribute", "id": aid, "subid": "", "field": "name",
                          "path": ATTR["put_name"].format(id=aid),
                          "body": {"external_id": aid, "name": dict(attr.get("name") or {})}})
    values = {v.get("external_id"): v.get("value") for v in (attr.get("values") or [])}
    for r in [r for r in rows if r["field"] == "value" and r.get("subid")]:
        vid = r["subid"]
        obj, planned = _merge_loc(values.get(vid), [r], locales, f"value[{vid}]", overwrite)
        if planned:
            planned_n += len(planned)
            print(f"  attribute/{aid}/value/{vid}: {', '.join(planned)}")
            puts.append((f"attribute/{aid}/value/{vid}",
                         ATTR["put_value"].format(id=aid, subid=vid),
                         {"external_id": vid, "value": obj}, len(planned)))
            snaps.append({"entity": "attribute", "id": aid, "subid": vid, "field": "value",
                          "path": ATTR["put_value"].format(id=aid, subid=vid),
                          "body": {"external_id": vid, "value": dict(values.get(vid) or {})}})
    return puts, planned_n, 0, snaps


# The admin API is rate-limited, so bulk writes are spaced out. Retries in api()
# handle a 429 that still slips through; this keeps them rare.
DEFAULT_PACE = 0.25


def _merge_nested(e, obj, rws, locales, overwrite, missing=None):
    """Merge nested-member translations into a copy of `obj` -> (obj, planned).

    Must be applied in the write pass too, not only when planning: the body is rebuilt
    from a fresh read to close the race window, and anything merged into the planning
    copy alone never reaches the server. That failed silently once — the PUT returned
    204 with the top-level fields translated and every step name still in English.
    """
    n = e.get("nested")
    missing = [] if missing is None else missing
    if not n:
        return obj, []
    members = json.loads(json.dumps(obj.get(n["collection"]) or []))
    have = {str(m.get(n["id"])) for m in members}
    # A row pointing at a member the object no longer has would otherwise be dropped in
    # silence: the loop below only walks members that exist, so the translation just
    # never lands and the run still says success.
    for r in rws:
        if r.get("field") == n["row_field"] and str(r.get("subid")) not in have:
            missing.append(f"{n['collection']}[{r.get('subid')}] no longer exists on "
                           f"this object — its translation was NOT written")
    planned, changed = [], False
    for member in members:
        sub = str(member.get(n["id"]))
        srows = [r for r in rws
                 if r["field"] == n["row_field"] and str(r.get("subid")) == sub]
        if not srows:
            continue
        m, p = _merge_loc(member.get(n["field"]), srows, locales,
                          f"{n['collection']}[{sub}]", overwrite)
        if p:
            member[n["field"]] = m; planned += p; changed = True
    return (dict(obj, **{n["collection"]: members}) if changed else obj), planned


def _snapshot(path, objects):
    """Write the pre-write state of every object about to be touched.

    A catalog PUT REPLACES the object, so there is no server-side undo: without
    this, a bad --overwrite run is unrecoverable. Full objects, not just the
    translated cells, because that is what `restore` has to PUT back.

    Writes that do not address a whole object — attribute name, attribute value —
    contribute a raw-PUT record instead: the path plus the body that puts the
    pre-write state back. Both shapes live in the same list, so a run that mixes
    attributes with flat entities rolls back in one `restore`.
    """
    out = path or (f"catalog-snapshot-{time.strftime('%Y%m%d-%H%M%S')}.json")
    payload = {"taken": time.strftime("%Y-%m-%dT%H:%M:%S"), "objects": objects}
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    except OSError as exc:
        sys.exit(f"refusing to write without a snapshot: cannot create {out} "
                 f"({exc.strerror}). Fix the path or pass --no-snapshot to accept "
                 f"that the write cannot be rolled back.")
    print(f"  snapshot of {len(objects)} record(s) -> {out}")
    print(f"    roll back with:  catalog_i18n.py restore {out} --write")
    return out


def restore(env, path, write=False, pace=DEFAULT_PACE):
    """PUT a snapshot back, object by object. Previews unless --write."""
    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
    except OSError as exc:
        sys.exit(f"restore: cannot read {path}: {exc.strerror}")
    except json.JSONDecodeError as exc:
        sys.exit(f"restore: {path} is not valid JSON — {exc}")
    objects = snap.get("objects") or []
    if not objects:
        sys.exit(f"restore: {path} contains no objects")
    print(f"snapshot taken {snap.get('taken', '?')}, {len(objects)} object(s)")

    written = failed = 0
    for i, rec in enumerate(objects):
        ent, oid, obj = rec.get("entity"), rec.get("id"), rec.get("object")
        # Two record shapes. A whole-object record carries `object` and its body is
        # rebuilt the same way a write builds it. A raw-PUT record already carries
        # its own `path` and `body`, because the write it undoes did not address a
        # whole object either (attribute name, attribute value).
        if rec.get("path") and isinstance(rec.get("body"), dict):
            vid = rec.get("subid")
            label = f"{ent}/{oid}" + (f"/value/{vid}" if vid
                                      else f" {rec.get('field', '')}".rstrip())
            put_path, body, api_v = rec["path"], rec["body"], "v2"
            payload = rec["body"].get(rec.get("field") or "")
            what = f"{len(payload)} locale(s)" if isinstance(payload, dict) else "1 value"
            if isinstance(payload, dict) and not payload:
                # Nothing was there before the write, so putting that state back means
                # blanking the field. Say so: the API may well refuse an empty name.
                print(f"  ! {label} was EMPTY before the write — restoring it clears the "
                      f"field, and Xsolla may reject that. Check this one by hand.")
        else:
            e = ENTITIES.get(ent)
            if not e or not isinstance(obj, dict):
                print(f"  ! skip {ent}/{oid}: unknown entity or malformed record")
                failed += 1
                continue
            label = f"{ent}/{oid}"
            put_path, body, api_v = (e["path"].format(id=oid), _put_body(e, obj, {}),
                                     e.get("api", "v2"))
            what = f"{len(obj)} field(s)"
        print(f"  {label}: restore {what}")
        if not write:
            continue
        if i and pace > 0:
            time.sleep(pace)
        st, resp = api(env, "PUT", put_path, body, api_version=api_v)
        if st in OK_STATUS:
            written += 1
            print(f"    -> PUT {st}")
        else:
            failed += 1
            print(f"    -> PUT {st} FAILED {resp}")
    print()
    if not write:
        print(f"PREVIEW ONLY — nothing restored. Re-run with --write to apply.")
        return 0
    print(f"restored {written} write(s)" + (f"; {failed} FAILED" if failed else ""))
    return 1 if failed else 0


class _Backup:
    """A CSV of the CURRENT server state of every string about to be replaced.

    Not a substitute for the JSON snapshot: that one is for `restore`, machine to
    machine. This one is for a person — same wide schema as the working
    CSV, so a translation that is about to be overwritten stays readable, diffable and
    re-importable on its own.

    It is written from the fresh read taken immediately before each object's own PUT,
    and flushed per object, so it always reflects what was really on the server at the
    moment of the overwrite — and it is complete for everything already written even if
    the run dies half way through.
    """

    def __init__(self, path, locales, source="en"):
        # The source column is what makes this file re-importable rather than merely
        # readable: `_cols` requires a source plus at least one target, so a backup
        # written with target locales alone was refused by the very command it exists
        # to feed ("only one language column"). It is taken from the server's own
        # source-locale text, so the file round-trips through `import --overwrite`.
        self.source = source
        self.locales = [l for l in locales if l != source]
        self.path = path or f"catalog-backup-{time.strftime('%Y%m%d-%H%M%S')}.csv"
        self.rows = 0
        try:
            self.fh = open(self.path, "w", newline="", encoding="utf-8")
        except OSError as exc:
            sys.exit(f"refusing to write without a backup of the current translations: "
                     f"cannot create {self.path} ({exc.strerror}). Fix the path or pass "
                     f"--no-backup to accept that.")
        self.w = csv.writer(self.fh)
        self.w.writerow(META_COLS + [self.source] + list(self.locales))
        self.fh.flush()

    def add(self, ent, oid, fields, obj, nested=None):
        for field in fields:
            cur = obj.get(field)
            if not isinstance(cur, dict):
                continue
            self.w.writerow([ent, oid, "", field, "server state before the write"]
                            + [cur.get(self.source, "")]
                            + [cur.get(l, "") for l in self.locales])
            self.rows += 1
        # Nested members are replaced by the same PUT, so leaving them out would back up
        # half the write — a reward chain's step names could be overwritten with nothing
        # kept.
        for member in (obj.get(nested["collection"]) or []) if nested else []:
            cur = member.get(nested["field"])
            if not isinstance(cur, dict):
                continue
            self.w.writerow([ent, oid, str(member.get(nested["id"])), nested["row_field"],
                             "server state before the write"]
                            + [cur.get(self.source, "")]
                            + [cur.get(l, "") for l in self.locales])
            self.rows += 1
        self.fh.flush()

    def close(self):
        self.fh.close()


def _verify_written(env, put_path, info):
    """Read the object back and prove the write did what it said.

    A 204 says the request was accepted, not that every field survived. The
    run-level check (a second import planning 0 changes) catches "didn't write";
    it cannot catch "wrote and ate something", because a field that was dropped
    never reappears in the plan. The snapshot is already in memory, so this diff
    is nearly free.
    """
    st, after = api(env, "GET", put_path,
                    api_version=(info.get("e") or {}).get("api", "v2"))
    if st != 200:
        return [f"could not read back to verify (GET {st}) — check this object by hand"]
    problems = []
    sent = info.get("sent") or {}
    # Only a field that EXISTED before and is gone afterwards is data loss. The body
    # legitimately carries a few defaults `_shape` adds (`is_enabled`), and the server
    # is free not to echo those — flagging them would cry wolf on every clean write.
    before = info.get("before") or {}
    lost = [k for k in sent if k not in DERIVED and k in before and k not in after]
    if lost:
        problems.append("fields sent but MISSING after the write: " + ", ".join(sorted(lost))
                        + " — re-send them")
    # ONLY the localizable fields are locale maps. Checking every dict-valued field
    # reads `limits` as one and reports `recurrent_schedule` as a locale that did not
    # land — the server legitimately rebases the schedule's displayable window on a
    # write, so that fired on every item carrying a recurring limit.
    for field in (info.get("e") or {}).get("fields", ()):
        obj = sent.get(field)
        if not isinstance(obj, dict):
            continue
        got = after.get(field)
        if not isinstance(got, dict):
            problems.append(f"{field}: gone or not a localization object after the write")
            continue
        missing = [l for l, v in obj.items() if got.get(l) != v]
        if missing:
            problems.append(f"{field}: locale(s) did not land as sent: "
                            + ", ".join(sorted(missing)))
    # Nested members are the easy thing to miss: the top-level fields land, the PUT
    # answers 204, and every step name is still in the source language.
    n = (info.get("e") or {}).get("nested")
    if n:
        sent_members = {str(m.get(n["id"])): (m.get(n["field"]) or {})
                        for m in (sent.get(n["collection"]) or [])}
        got_members = {str(m.get(n["id"])): (m.get(n["field"]) or {})
                       for m in (after.get(n["collection"]) or [])}
        for sub, want in sent_members.items():
            have = got_members.get(sub)
            if have is None:
                problems.append(f"{n['collection']}[{sub}]: gone after the write")
                continue
            bad = [l for l, v in want.items() if have.get(l) != v]
            if bad:
                problems.append(f"{n['collection']}[{sub}]: locale(s) did not land: "
                                + ", ".join(sorted(bad)))
    return problems


def import_csv(env, path, source=None, overwrite=False, write=False, allow_field_loss=False,
               pace=DEFAULT_PACE, snapshot=True, snapshot_path=None,
               on_conflict="skip", verify=True, backup=True, backup_path=None,
               allow_unverified=False):
    fieldnames, rows = _read_csv(path)
    if not rows:
        sys.exit("empty CSV")
    # First line of the run, before the plan: what the user approves has to say which
    # catalog it lands in.
    print(f"  target: {_project_line(env)}" + ("  [WRITE]" if write else "  [preview]"))
    src, locales = _cols(fieldnames, path, announce=True, source=source)
    # Refuse to start, like an unknown locale does. Importing with the source column
    # misidentified silently drops a whole finished locale, and the plan cannot show
    # that: the rows for the swallowed locale simply are not there.
    if not source:
        prob = _source_column_problem(src, locales)
        if prob:
            sys.exit(f"import: {prob}")

    # An unknown locale returns 404 and drops the WHOLE PUT — valid locales in the
    # same request are lost too. Refuse before touching the network; `check` is a
    # separate step the caller can skip, so import must not rely on it.
    # A known 5-letter code is normalized down (the API answers in 2-letter, so
    # keying by 5 would compare against nothing and re-write every run).
    canon, bad = {}, []
    for loc in locales:
        c = _norm_locale(loc)
        if c:
            canon[loc] = c
        else:
            bad.append(loc)
    if bad:
        sys.exit(f"refusing to import: {', '.join(repr(b) for b in bad)} is not a catalog "
                 f"locale — an unknown locale 404s and drops the entire write. "
                 f"Fix the column header(s) (see references/supported-languages.md), "
                 f"or run `check` for the full report.")
    renamed = {k: v for k, v in canon.items() if k != v}
    if renamed:
        print("  normalized locale(s): " + ", ".join(f"{k} -> {v}" for k, v in sorted(renamed.items())))
        for r in rows:
            for col, c in renamed.items():
                if (r.get(col) or "").strip() and not (r.get(c) or "").strip():
                    r[c] = r[col]
    locales = sorted(set(canon.values()))

    grouped, unaddressable = {}, []
    for r in rows:
        prob = _row_problem(r)
        if prob:
            unaddressable.append(f"{r.get('entity')}/{r.get('id')}/{r.get('field')}: {prob}")
            continue
        grouped.setdefault((r["entity"], r["id"]), []).append(r)
    if unaddressable:
        print(f"  ! {len(unaddressable)} row(s) address nothing and were NOT imported:")
        for u in unaddressable:
            print(f"    {u}")
    for clash in _conflicting_rows(rows, locales):
        print(f"  ! two different translations for one cell, first one used — {clash}")
    # `check` is a separate command the caller can skip, so run its hard value checks
    # here too — not to block (import guards data loss, not content), but so the plan
    # being approved does not quietly contain a broken placeholder or tag.
    value_issues = _hard_value_issues(rows, src, locales)
    if value_issues:
        print(f"  ! {len(value_issues)} QA issue(s) in the values themselves — these "
              f"would be written as-is:")
        for v in value_issues[:5]:
            print(f"    {v}")
        if len(value_issues) > 5:
            print(f"    ... and {len(value_issues) - 5} more")
        print(f"    -> run `check {path}` for the full report before approving.")

    # --- pass 1: plan. Nothing is written here, so the snapshot taken before pass 2
    # covers the WHOLE run. This used to be one pass that wrote the snapshot from
    # inside the write loop, on the first object that needed a PUT: it captured that
    # single object while the run went on to REPLACE many more, so `restore` silently
    # undid only the first one. Splitting the passes is what makes the documented
    # invariant ("snapshot before the first PUT") literally true.
    puts, snap_objects, wipes = [], [], []
    failed_rows = len(unaddressable)
    # Pass 1 records the state each plan was made against. Pass 2 re-reads the
    # object immediately before writing and compares ONLY the fields it is about to
    # replace: the body is rebuilt from the fresh read, so a concurrent edit to any
    # other field survives by construction, and the localized fields are the entire
    # conflict surface.
    plans = {}
    unverified = set()       # entities whose write form has never been exercised live
    blocked = []             # objects the API will not let us update at all right now
    touched = set()          # objects with at least one planned change
    planned_n = 0
    failed = failed_rows
    for (ent, oid), rws in grouped.items():
        if ent == "attribute":
            p, n, f_, snaps = plan_attribute(env, oid, rws, locales, overwrite)
            puts += [(lbl, pth, bdy, cnt, None, None) for lbl, pth, bdy, cnt in p]
            snap_objects += snaps
            planned_n += n; failed += f_
            if p:
                touched.add((ent, oid))
            continue
        e = ENTITIES.get(ent)
        if not e:
            print(f"  ! skip {ent}/{oid}: unknown entity"); failed += 1; continue
        st, obj = api(env, "GET", e["path"].format(id=oid), api_version=e.get("api", "v2"))
        if st != 200:
            print(f"  ! skip {ent}/{oid}: GET {st}"); failed += 1; continue
        merged, planned = {}, []
        for field in e["fields"]:
            frows = [r for r in rws if r["field"] == field and not r.get("subid")]
            if not frows:
                continue
            m, p = _merge_loc(obj.get(field), frows, locales, field, overwrite)
            merged[field] = m; planned += p
        gone = []
        # Keep the pre-merge read for the snapshot. `_merge_nested` returns a NEW dict
        # with the translations already written into its members, so snapshotting the
        # merged copy captured a nested member as it was ABOUT to be, not as it was —
        # and `restore` then put the translation back instead of removing it. The PUT
        # answered 204 and the rollback looked clean while the step name stayed
        # translated. Top-level fields were never affected (they go into `merged`, not
        # into `obj`), which is why only nested members were un-rollbackable. Same
        # defect, and same fix, as the backup CSV further down.
        pre_nested = obj
        obj, nested_planned = _merge_nested(e, obj, rws, locales, overwrite, gone)
        planned += nested_planned
        for g in gone:
            print(f"  ! {ent}/{oid}: {g}")
            failed += 1
        if not planned:
            continue

        # Some entities refuse EVERY update while they are live — Xsolla answers
        # 422/6209 for a running chain. Catch that here, before the object joins the
        # plan, so the preview stays honest: what the user approves is what can actually
        # be carried out, the counts exclude it, no doomed PUT is sent, and it is not
        # reported later as a mysterious failure.
        #
        # This tool never changes a chain's state to get around that. Disabling a live
        # chain takes it away from players and its effect on their progress is unknown,
        # which is far outside what "translate some names" should be allowed to do. The
        # chain is skipped; whoever owns it can take it out of service and re-run.
        flag = e.get("no_write_while_active")
        if flag and obj.get(flag):
            blocked.append(f"{ent}/{oid}")
            print(f"  {ent}/{oid}: {', '.join(planned)}")
            print(f"    ‼ BLOCKED, excluded from the plan: this {ent} is active, and "
                  f"Xsolla refuses any update to a running chain. This tool does not "
                  f"disable chains — it can be localized once it is out of service.")
            continue

        planned_n += len(planned)
        touched.add((ent, oid))
        print(f"  {ent}/{oid}: {', '.join(planned)}")
        snap_objects.append({"entity": ent, "id": oid, "object": pre_nested})
        lost = _dropped(e, obj, allow_field_loss)
        if lost:
            wipes.append(f"{ent}/{oid}: {', '.join(lost)}")
            print(f"    !! this write would WIPE: {', '.join(lost)}")
        if e.get("write_unverified"):
            unverified.add(ent)
        plans[(ent, oid)] = {"e": e, "rows": rws, "base": obj, "fields": list(merged)}
        puts.append((f"{ent}/{oid}", e["path"].format(id=oid),
                     _put_body(e, obj, merged, allow_field_loss), len(planned), ent, oid))

    print()
    if not write:
        print(f"PREVIEW ONLY — nothing written. {planned_n} translation(s) would change "
              f"across {len(touched)} of {len(grouped)} object(s) in the CSV.")
        if snapshot and snap_objects:
            print(f"  a snapshot of the {len(snap_objects)} affected record(s) will be "
                  f"saved before the first write, so the run can be rolled back.")
        if blocked:
            print(f"  {len(blocked)} object(s) are active and cannot be written, so "
                  f"they are excluded: {', '.join(blocked)}. Their translations stay in "
                  f"the CSV and import fine once they are out of service.")
        if unverified:
            print(f"  {len(unverified)} entity type(s) have an UNVERIFIED write form "
                  f"({', '.join(sorted(unverified))}) — reading and translating them is "
                  f"fine, but --write refuses until one has been exercised live. See "
                  f"references/coverage-matrix.md.")
        if wipes:
            print(f"  {len(wipes)} object(s) would lose fields — see '!!' above. Do not "
                  f"proceed until that is resolved.")
        if failed:
            print(f"  {failed} row(s)/object(s) could not be addressed or read "
                  f"(see '!' above).")
        print("Re-run with --write to apply.")
        # A preview that reported failures must NOT exit 0. This is the step the agent
        # runs before asking for approval, and the skill's contract is that a non-zero
        # exit is a failure — returning 0 here made every unaddressable row and failed
        # GET invisible to a caller checking the exit code, which is the same defect as
        # a `!` line that leaves the exit code alone.
        return 1 if failed else 0

    if unverified and not allow_unverified:
        sys.exit(f"refusing to write {', '.join(sorted(unverified))}: the write form for "
                 f"these entities has never been exercised against a live object, and a "
                 f"catalog PUT REPLACES it — the required-even-when-null fields and the "
                 f"keys that must be stripped are measured per entity, never guessed. Do "
                 f"a create -> localize -> verify -> restore run on one object first, "
                 f"then clear `write_unverified` for that entity. `--allow-unverified` "
                 f"overrides this; only use it with a snapshot and a rollback plan.")

    # --- pass 2: write. The snapshot lands first, or nothing is touched at all.
    snap_file = _snapshot(snapshot_path, snap_objects) if (snapshot and snap_objects) else None
    bak = _Backup(backup_path, locales, source=src) if backup else None
    if bak:
        print(f"  current translations will be backed up to {bak.path} as each object "
              f"is read, before it is replaced")

    written = ok = 0
    conflicts = []
    for i, (label, put_path, body, n, ent, oid) in enumerate(puts):
        if i and pace > 0:
            time.sleep(pace)

        info = plans.get((ent, oid)) if ent else None
        if info is not None:
            # Re-read RIGHT BEFORE this object's own write, not once for the batch:
            # the window that matters is per object, and it is the only one we can
            # shrink (these endpoints carry no ETag / If-Match).
            st, fresh = api(env, "GET", put_path, api_version=info["e"].get("api", "v2"))
            if st != 200:
                failed += 1
                print(f"  {label} -> re-read before write FAILED {st}; not written")
                continue
            changed = [f for f in info["fields"] if info["base"].get(f) != fresh.get(f)]
            if changed:
                detail = []
                for f in changed:
                    was, now = info["base"].get(f) or {}, fresh.get(f) or {}
                    locs = sorted(set(was) | set(now))
                    detail.append(f"{f}: " + ", ".join(
                        f"{l} {was.get(l)!r} -> {now.get(l)!r}" for l in locs
                        if was.get(l) != now.get(l)))
                conflicts.append(f"{label}: {' | '.join(detail)}")
                if on_conflict != "overwrite":
                    failed += 1
                    print(f"  {label} -> CONFLICT, not written: changed since export "
                          f"({'; '.join(detail)})")
                    continue
                print(f"  {label} -> CONFLICT overridden by --on-conflict overwrite")
            # Rebuild against the fresh object so any concurrent edit OUTSIDE the
            # translated fields is carried through instead of being replaced by a
            # stale copy.
            merged = {}
            for field in info["e"]["fields"]:
                frows = [r for r in info["rows"] if r["field"] == field]
                if not frows:
                    continue
                m, _p = _merge_loc(fresh.get(field), frows, locales, field, overwrite)
                merged[field] = m
            # Keep the pre-merge read: nested members are merged INTO the object, so
            # backing up the merged copy would record what we are about to write instead
            # of what is being replaced — a backup that preserves nothing.
            pre = fresh
            fresh, _np = _merge_nested(info["e"], fresh, info["rows"], locales, overwrite)
            body = _put_body(info["e"], fresh, merged, allow_field_loss)
            info["sent"], info["before"] = body, pre
            if bak:
                bak.add(ent, oid, info["fields"], pre, info["e"].get("nested"))

        st, resp = api(env, "PUT", put_path, body,
                       api_version=(info["e"].get("api", "v2") if info else "v2"))
        if st in OK_STATUS:
            written += n; ok += 1
            print(f"  {label} -> PUT {st}")
            if verify and info is not None:
                bad = _verify_written(env, put_path, info)
                if bad:
                    failed += 1
                    for msg in bad:
                        print(f"    !! {label}: {msg}")
        else:
            failed += 1
            print(f"  {label} -> PUT {st} FAILED {resp}")
            if "6209" in str(resp) or "Active chain cannot be updated" in str(resp):
                print(f"    hint: {label} is an ACTIVE chain — Xsolla refuses any update "
                      f"while it runs, and this tool does not change chain state to get "
                      f"around it. It has to be out of service before it can be "
                      f"localized.")

    if verify:
        n_attr_puts = sum(1 for _l, _p, _b, _n, e_, _o in puts if e_ is None)
        if n_attr_puts:
            print(f"  note: {n_attr_puts} attribute PUT(s) were not race-checked or "
                  f"verified — nested name/value writes have no single object to diff. "
                  f"They ARE in the snapshot, so the run is still rollbackable.")
    if conflicts:
        print()
        print(f"{len(conflicts)} object(s) changed between export and write:")
        for c in conflicts:
            print(f"  - {c}")
        if on_conflict != "overwrite":
            print("  Show both versions to the user and re-run those rows with "
                  "`--on-conflict overwrite` to apply the translation over the change, "
                  "or drop them to keep what is in the catalog.")

    print()
    print(f"wrote {written} translation(s) in {ok} successful PUT(s) "
          f"across {len(touched)} object(s).")
    if blocked:
        print(f"{len(blocked)} object(s) were excluded as active and unwritable: "
              f"{', '.join(blocked)}.")
    if snap_file:
        print(f"pre-write state saved in {snap_file} — "
              f"`restore {snap_file} --write` undoes this run.")
    if bak:
        bak.close()
        print(f"the {bak.rows} translation(s) that were on the server beforehand are in "
              f"{bak.path} — readable, and replayable with "
              f"`import {bak.path} --overwrite`.")
    if failed:
        print(f"{failed} object(s) FAILED — nothing was written for those. "
              f"Re-run to retry (import is fill-only, so a re-run is safe).")
    return 1 if failed else 0


# --- arg helpers ---------------------------------------------------------------

def _flag(argv, name, default=None):
    if name not in argv:
        return default
    i = argv.index(name) + 1
    if i >= len(argv):
        sys.exit(f"{name} needs a value")
    val = argv[i]
    if val.startswith("--"):
        sys.exit(f"{name} needs a value, got the flag '{val}' — a missing value used "
                 f"to bind the next flag as the value and silently use the default.")
    return val


def _positional(rest):
    """The single positional argument, skipping flags. An UNKNOWN flag is fatal:
    treating it as bare would silently swallow its value as the positional (a
    typo'd `--source fr` used to become the locale list)."""
    val, i = None, 0
    while i < len(rest):
        a = rest[i]
        if a in VALUE_FLAGS:
            i += 2
        elif a in BARE_FLAGS:
            i += 1
        elif a.startswith("--"):
            sys.exit(f"unknown flag '{a}'. Known: "
                     f"{', '.join(sorted(VALUE_FLAGS | BARE_FLAGS))}")
        else:
            val, i = a, i + 1
    return val


def _conflict_mode(argv):
    mode = (_flag(argv, "--on-conflict", "skip") or "skip").strip()
    if mode not in ("skip", "overwrite"):
        sys.exit(f"--on-conflict: '{mode}' — expected 'skip' (default) or 'overwrite'")
    return mode


def _validate_flags(argv):
    """Reject an unknown flag for EVERY command, not just the ones that parse a
    positional. A silently ignored `--wirte` reads to the caller as a flag that was
    honoured, which is the worst possible failure mode for a write guard."""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in VALUE_FLAGS:
            i += 2
            continue
        if a.startswith("--") and a not in BARE_FLAGS:
            sys.exit(f"unknown flag '{a}'. Known: "
                     f"{', '.join(sorted(VALUE_FLAGS | BARE_FLAGS))}")
        i += 1


def main():
    argv = sys.argv
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd = argv[1]
    _validate_flags(argv[2:])
    if cmd == "discover":
        discover(load_env(argv)); return
    if cmd == "langs":
        langs(load_env(argv)); return
    if len(argv) < 3:
        sys.exit(__doc__)
    target = argv[2]
    if cmd == "export":
        env = load_env(argv)
        raw_locales = [l.strip() for l in (_positional(argv[3:]) or "ru,de").split(",") if l.strip()]
        source = _flag(argv, "--source", "en").strip()
        bad = {l: _norm_locale(l) for l in raw_locales + [source]}
        unknown = [l for l, c in bad.items() if not c]
        if unknown:
            sys.exit(f"export: {', '.join(repr(u) for u in unknown)} is not an Xsolla "
                     f"catalog locale — see references/supported-languages.md.")
        locales = [bad[l] for l in raw_locales]
        source = bad[source]
        if source in locales:
            sys.exit(f"export: source '{source}' is also a target locale — drop it "
                     f"from the target list.")
        entities = [e.strip() for e in (_flag(argv, "--entity", "items")).split(",") if e.strip()]
        sys.exit(export(env, target, locales, entities, source=source,
                        only_missing=("--missing" in argv)))
    elif cmd == "batch":
        batch(target, _flag(argv, "--locale"), int(_flag(argv, "--size", "50")))
    elif cmd == "fill":
        sys.exit(fill(target, _flag(argv, "--locale"), _flag(argv, "--from")))
    elif cmd == "merge":
        src = _flag(argv, "--from")
        if not src:
            sys.exit("merge: --from PATH required (the partner's CSV to load)")
        sys.exit(merge(target, src, overwrite=("--overwrite" in argv)))
    elif cmd == "restore":
        sys.exit(restore(load_env(argv), target, write=("--write" in argv),
                         pace=float(_flag(argv, "--pace", str(DEFAULT_PACE)))))
    elif cmd == "check":
        sys.exit(check(target, _flag(argv, "--max-len", ""),
                       source=_flag(argv, "--source")))
    elif cmd == "import":
        if "--dry" in argv and "--write" in argv:
            sys.exit("import: --dry and --write are contradictory; pick one")
        mode = _conflict_mode(argv)          # validate flags before touching credentials
        sys.exit(import_csv(load_env(argv), target,
                            source=_flag(argv, "--source"),
                            overwrite=("--overwrite" in argv),
                            write=("--write" in argv),
                            allow_field_loss=("--allow-field-loss" in argv),
                            pace=float(_flag(argv, "--pace", str(DEFAULT_PACE))),
                            snapshot=("--no-snapshot" not in argv),
                            snapshot_path=_flag(argv, "--snapshot"),
                            on_conflict=mode,
                            verify=("--no-verify" not in argv),
                            backup=("--no-backup" not in argv),
                            backup_path=_flag(argv, "--backup"),
                            allow_unverified=("--allow-unverified" in argv)))
    else:
        sys.exit(f"unknown command: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main()
