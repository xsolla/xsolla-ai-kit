#!/usr/bin/env python3
"""Offline test suite for catalog_i18n.py — no network, no credentials, no live project.

    python3 skills/localization/scripts/test_catalog_i18n.py

Every case here is a defect that actually shipped, or an invariant whose violation
shipped. They share one shape: **work discarded without a word** — a row that addressed
nothing, a guard that printed but did not gate, a snapshot that covered 1 of N. A
1-object happy-path test cannot see any of them, which is why they survived three
review rounds.

`api()` is stubbed, so this exercises planning, addressing, CSV handling and the
write-ordering invariants. It does NOT re-measure the API's write form — the 422/1102
rules and the pass-through field list are empirical and live in references/write-safety.md.
"""
import contextlib, csv, importlib.util, io, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ci", os.path.join(HERE, "catalog_i18n.py"))
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

# Shaped exactly like load_env()'s return: a dict of env vars, not a bespoke struct.
# It used to be {"pid":…, "key":…}, which no code path actually produces — so anything
# reading env["XSOLLA_PROJECT_ID"] was untestable and the suite could not have caught it.
ENV = {"XSOLLA_PROJECT_ID": "999999", "XSOLLA_PROJECT_API_KEY": "dummy"}
H = ["entity", "id", "subid", "field", "context", "en", "de"]
ITEM = {"sku": "x", "item_id": 1, "name": {"en": "Sword"}, "description": {"en": "A sword"},
        "image_url": "http://i/x.png", "groups": ["g1"], "inventory_options": {}}
CHAIN = {"external_id": "c1", "name": {"en": "Chain"}, "description": {"en": "d"},
         "long_description": {"en": "l"}, "popup_header": {"en": "h"},
         "popup_instruction": {"en": "i"}, "steps": [{"step_id": 12, "name": {"en": "Step"}}]}

_results = []


def case(name):
    def deco(fn):
        _results.append((name, fn))
        return fn
    return deco


def write_csv(path, rows, header=H):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)
    return path


def stub(get_status=200, obj=None, put_status=204, log=None):
    """Replace api() with a canned responder; `log` collects (method, path)."""
    def api(env, method, path, body=None, api_version="v2", **kw):
        if log is not None:
            log.append((method, path, body))
        if method == "GET":
            return get_status, (json.loads(json.dumps(obj)) if obj is not None else dict(ITEM))
        return put_status, {}
    ci.api = api


def run(fn, *a, **kw):
    """-> (rc, stdout). A sys.exit is a result, not a crash: most guards exit."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = fn(*a, **kw)
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else 1
        buf.write(f"\n{e.code}\n")
    return rc, buf.getvalue()


def imp(rows, header=H, **kw):
    with tempfile.TemporaryDirectory() as d:
        p = write_csv(os.path.join(d, "t.csv"), rows, header)
        kw.setdefault("snapshot", False)
        kw.setdefault("backup", False)
        return run(ci.import_csv, ENV, p, **kw)


def chk(rows, header=H, **kw):
    with tempfile.TemporaryDirectory() as d:
        p = write_csv(os.path.join(d, "t.csv"), rows, header)
        return run(ci.check, p, **kw)


# --- the address: every part of it is consumed by an equality test somewhere ---------

@case("a row naming an unknown entity is refused, not dropped")
def _():
    stub()
    rc, out = imp([["itemz", "x", "", "name", "", "Sword", "Schwert"]])
    assert rc == 1, rc
    assert "address nothing" in out, out


@case("a field the entity does not have is refused (promotion has no description)")
def _():
    stub()
    rc, out = chk([["discount_promotion", "p1", "", "description", "", "Sale", "Rabatt"]])
    assert rc == 1, out
    assert "has no field" in out, out


@case("a blank id is refused (it addresses nothing)")
def _():
    stub()
    rc, out = imp([["items", "", "", "name", "", "Sword", "Schwert"]])
    assert rc == 1, out
    assert "empty id" in out, out


@case("surrounding whitespace in the address is normalized, not silently dropped")
def _():
    # Validation stripped while the plan loop matched raw, so `field=" name"` passed
    # check clean and then matched nothing: 0 changes, exit 0, no message.
    stub()
    rc, out = imp([["  items ", "x", "", " name ", "", "Sword", "Schwert"]])
    assert rc == 0, out
    assert "1 translation(s) would change" in out, out


@case("a subid on a top-level field is refused (it matches nothing)")
def _():
    # Excluded from the top-level pass by `not r.get("subid")`, then never seen again
    # because _merge_nested returns early for an entity with no nested members.
    stub()
    rc, out = imp([["items", "x", "7", "name", "", "Sword", "Schwert"]])
    assert rc == 1, out
    assert "top-level field" in out, out


@case("a nested field WITHOUT a subid is refused")
def _():
    stub(obj=CHAIN)
    rc, out = imp([["reward_chain", "c1", "", "step_name", "", "Step", "Schritt"]])
    assert rc == 1, out
    assert "subid is required" in out, out
    stub()
    rc, out = imp([["attribute", "a1", "", "value", "", "Rare", "Selten"]])
    assert rc == 1, out


@case("attribute name with a stray subid is refused")
def _():
    stub()
    rc, out = imp([["attribute", "a1", "v1", "name", "", "Rarity", "Seltenheit"]])
    assert rc == 1, out


HDR_FR = "entity,id,subid,field,fr" + chr(10)
ROW_OK = "items,x,,name,Epee" + chr(10)
ROW_ACCENT = ("items,x,,name,pr" + chr(233) + "cieux" + chr(10)).encode("latin-1")
HDR_DUP = "entity,id,subid,field,fr,fr" + chr(10)
ROW_DUP = "items,x,,name,A,B" + chr(10)
HDR_SEMI = "entity;id;subid;field;fr" + chr(10)
ROW_SEMI = "items;x;;name;A" + chr(10)
BLANKS = chr(10) + ",,,," + chr(10)


@case("a partner CSV goes through the same hardened reader as every other file")
def _():
    # merge used a bare DictReader, so the one file that arrives from OUTSIDE was the
    # only one with no guards: Latin-1 raised a raw UnicodeDecodeError, a duplicate
    # column silently kept the last value, a semicolon file got a misleading "missing
    # required column(s)", and Excel's trailing blank rows read as missing strings.
    with tempfile.TemporaryDirectory() as d:
        work = write_csv(os.path.join(d, "w.csv"),
                         [["items", "x", "", "name", "", "Sword", ""]])

        def merge_from(name, data, binary=False):
            p = os.path.join(d, name)
            if binary:
                open(p, "wb").write(data)
            else:
                open(p, "w", newline="").write(data)
            return run(ci.merge, work, p)

        rc, out = merge_from("latin1.csv", HDR_FR.encode("latin-1") + ROW_ACCENT, binary=True)
        assert rc == 1 and "not valid UTF-8" in out, out

        rc, out = merge_from("dup.csv", HDR_DUP + ROW_DUP)
        assert rc == 1 and "duplicate column" in out, out

        rc, out = merge_from("semi.csv", HDR_SEMI + ROW_SEMI)
        assert rc == 1 and "semicolon-delimited" in out, out

        rc, out = merge_from("blank.csv", HDR_FR + ROW_OK + BLANKS)
        assert rc == 0 and "NOT loaded" not in out, out


HDR_META = "entity,id,subid,field,fr,translator,notes" + chr(10)
ROW_META = "items,x,,name,Epee,Marie,ok" + chr(10)
HDR_BADLOC = "entity,id,subid,field,fr_CA" + chr(10)
ROW_BADLOC = "items,x,,name,Epee" + chr(10)
HDR_ONLYMETA = "entity,id,subid,field,translator" + chr(10)
ROW_ONLYMETA = "items,x,,name,Marie" + chr(10)


@case("translator metadata columns are ignored, but a bad locale is still fatal")
def _():
    # Real TMS and XLIFF exports add `translator`/`status`/`notes`, and rejecting the
    # whole file over them made the publisher path brittle. But a locale-SHAPED name
    # that does not resolve (`fr_CA`) must stay fatal: skipping it would silently
    # discard the translator's work.
    with tempfile.TemporaryDirectory() as d:
        work = write_csv(os.path.join(d, "w.csv"),
                         [["items", "x", "", "name", "", "Sword", ""]])

        def merge_from(name, text):
            p = os.path.join(d, name)
            open(p, "w", newline="").write(text)
            return run(ci.merge, work, p)

        rc, out = merge_from("meta.csv", HDR_META + ROW_META)
        assert rc == 0, out
        assert "ignoring non-locale column(s): notes, translator" in out, out

        rc, out = merge_from("badloc.csv", HDR_BADLOC + ROW_BADLOC)
        assert rc == 1 and "not Xsolla catalog locales" in out, out

        rc, out = merge_from("onlymeta.csv", HDR_ONLYMETA + ROW_ONLYMETA)
        assert rc == 1 and "no locale columns to merge" in out, out


@case("a legitimate nested address still plans (no false positive)")
def _():
    stub(obj=CHAIN)
    rc, out = imp([["reward_chain", "c1", "", "name", "", "Chain", "Kette"],
                   ["reward_chain", "c1", "12", "step_name", "", "Step", "Schritt"]])
    assert rc == 0, out
    assert "2 translation(s) would change" in out, out


@case("attribute/reward_chain fields pass check unflagged")
def _():
    rc, out = chk([["reward_chain", "c1", "", "popup_header", "", "Hi", "Hallo"],
                   ["reward_chain", "c1", "12", "step_name", "", "Step", "Schritt"],
                   ["attribute", "a1", "", "name", "", "Rarity", "Seltenheit"],
                   ["attribute", "a1", "v1", "value", "", "Rare", "Selten"]])
    assert rc == 0, out


# --- the CSV itself -----------------------------------------------------------------

@case("a duplicate column name is refused (DictReader keeps only the last)")
def _():
    # `en,de,de` discards the first `de` INSIDE the parser, before any guard can
    # compare them — undetectable downstream, so it has to be refused at read time.
    rc, out = chk([["items", "x", "", "name", "", "Sword", "Schwert", "Klinge"]],
                  header=H + ["de"])
    assert rc == 1, out
    assert "duplicate column" in out, out


@case("a reordered source column blocks in check and refuses in import")
def _():
    # The first attempt printed a `!` and still exited 0 — the skill's contract says
    # `!` blocks, so a reordered file sailed through QA.
    rows = [["items", "x", "", "name", "", "Schwert", "Sword"]]
    hdr = ["entity", "id", "subid", "field", "context", "de", "en"]
    rc, out = chk(rows, header=hdr)
    assert rc == 1, out
    assert "SOURCE column" in out, out
    stub()
    rc, out = imp(rows, header=hdr)
    assert rc == 1, out


@case("a partner file with no `en` column is refused, not silently half-imported")
def _():
    # `_source_column_problem` only fired when `en` sat to the RIGHT of the source, so a
    # translator's `de,fr` file (no `en` at all) sailed through both check and import:
    # `de` was read as the source, its contents were never written, and both reported a
    # clean exit. `merge` was taught to treat every column as a target; these were not.
    hdr = ["entity", "id", "subid", "field", "context", "de", "fr"]
    row = [["items", "x", "", "name", "", "Edelsteine", "Epee"]]
    rc, out = chk(row, header=hdr)
    assert rc == 1 and "no 'en' column" in out, out
    assert "merge" in out, "should point at merge, which handles partner files"
    stub()
    rc, out = imp(row, header=hdr)
    assert rc == 1, out
    # Naming the source explicitly is the documented escape, and must still work.
    rc, out = chk(row, header=hdr, source="de")
    assert rc == 0, out
    stub()
    rc, out = imp(row, header=hdr, source="de")
    assert rc == 0 and "name.fr='Epee'" in out, out


@case("--source names the source explicitly and repairs the column order")
def _():
    rows = [["items", "x", "", "name", "", "Schwert", "Sword"]]
    hdr = ["entity", "id", "subid", "field", "context", "de", "en"]
    rc, out = chk(rows, header=hdr, source="de")     # genuinely German-authored
    assert rc == 0, out
    rc, out = chk(rows, header=hdr, source="en")     # reordered file, repaired
    assert rc == 0, out
    assert "source column: 'en'" in out, out


@case("two different translations for one cell are surfaced, not silently resolved")
def _():
    rc, out = chk([["items", "x", "", "name", "", "Sword", "Schwert"],
                   ["items", "x", "", "name", "", "Sword", "Klinge"]])
    assert rc == 1, out
    assert "two different translations" in out, out


@case("a translated cell with an empty source is flagged as unverifiable")
def _():
    rc, out = chk([["items", "x", "", "name", "", "", "Schwert"]])
    assert rc == 0, out                       # not data loss, so a warning
    assert "cannot run" in out, out


@case("--max-len rejects limits below 1 and a missing field name")
def _():
    for bad in ("-5", "0", "name=-1", "=30"):
        rc, out = chk([["items", "x", "", "name", "", "Sword", "Schwert"]], max_len=bad)
        assert rc == 1, (bad, out)
    rc, out = chk([["items", "x", "", "name", "", "Sword", "Schwert"]], max_len="name=30")
    assert rc == 0, out


@case("an unknown locale column blocks (it 404s and drops the whole PUT)")
def _():
    rc, out = chk([["items", "x", "", "name", "", "Sword", "x"]],
                  header=["entity", "id", "subid", "field", "context", "en", "pt-PT"])
    assert rc == 1, out


# --- reporting: a counted failure must reach the exit code --------------------------

@case("import PREVIEW exits non-zero when it reported failures")
def _():
    # The write path returned `1 if failed`, the preview branch returned 0 outright —
    # so every unaddressable row was invisible to a caller checking $?, and preview is
    # the step the agent runs before asking for approval.
    stub()
    rc, out = imp([["itemz", "x", "", "name", "", "Sword", "Schwert"]])
    assert rc == 1, out
    assert "PREVIEW ONLY" in out, out


@case("a failed GET is reported as one skipped object, not a traceback")
def _():
    stub(get_status=404)
    rc, out = imp([["items", "x", "", "name", "", "Sword", "Schwert"]])
    assert rc == 1, out
    assert "GET 404" in out, out


@case("an attribute whose GET fails does not crash the run")
def _():
    # plan_attribute's error path returned a 3-tuple while the caller unpacked 4.
    stub(get_status=404)
    rc, out = imp([["attribute", "a1", "", "name", "", "Rarity", "Seltenheit"]])
    assert rc == 1, out
    assert "skip attribute/a1" in out, out


@case("every run names the project it targets, and whether it will write")
def _():
    # The plan lists entity/id/field/locale but never said which CATALOG — so a stale
    # XSOLLA_PROJECT_ID could aim an irreversible write at the wrong project with
    # nothing on screen to catch it.
    stub()
    rc, out = imp([["items", "x", "", "name", "", "Sword", "Schwert"]])
    assert "project 999999" in out, out
    assert "[preview]" in out, out
    stub()
    rc, out = imp([["items", "x", "", "name", "", "Sword", "Schwert"]],
                  write=True, verify=False)
    assert "project 999999" in out and "[WRITE]" in out, out


@case("import surfaces hard value issues on the plan when check was skipped")
def _():
    # `check` is a separate command, so a plan could quietly contain a renamed
    # placeholder or an unbalanced tag and get a "yes".
    stub()
    rc, out = imp([["items", "x", "", "name", "", "Gems {count} <b>a</b>",
                    "Gemmes {nombre} <b>a"]])
    assert rc == 0, out                      # a warning, not a block: import guards data
    assert "QA issue(s) in the values themselves" in out, out
    assert "placeholder mismatch" in out and "markup mismatch" in out, out
    # a clean value must not warn
    stub()
    rc, out = imp([["items", "x", "", "name", "", "Gems {count}", "Gemmes {count}"]])
    assert rc == 0 and "QA issue" not in out, out


@case("preview writes nothing at all")
def _():
    log = []
    stub(log=log)
    rc, out = imp([["items", "x", "", "name", "", "Sword", "Schwert"]])
    assert rc == 0, out
    assert not [c for c in log if c[0] == "PUT"], log


# --- reading: a failed list must be reported, never a traceback ----------------------

@case("a failed list returns empty + its status, not a traceback")
def _():
    # api() hands back the error BODY (a string) as the payload on any HTTP or network
    # failure, and fetch_all passed that straight to _as_list, which called .get() on
    # it. Every failed list died with AttributeError — so `discover` could never print
    # "(list failed HTTP n)" and `export` could never print INCOMPLETE.
    for resp in ((500, '{"errorMessage":"boom"}'), (0, "network error: timed out")):
        ci.api = lambda e, m, p, body=None, api_version="v2", r=resp: r
        objs, st = ci.fetch_all(ENV, "/admin/items/virtual_items")
        assert objs == [] and st == resp[0], (objs, st, resp)


@case("discover survives one failing entity list and still reports the rest")
def _():
    def api(env, method, path, body=None, api_version="v2", **kw):
        if "groups" in path:
            return 500, '{"errorMessage":"boom"}'
        if "virtual_items" in path:
            return 200, [dict(ITEM)]
        return 200, []
    ci.api = api
    rc, out = run(ci.discover, ENV)
    assert "groups" in out and "list failed HTTP 500" in out, out
    assert "items" in out, out


@case("export reports INCOMPLETE and exits non-zero when a list fails")
def _():
    ci.api = lambda e, m, p, body=None, api_version="v2": (500, '{"errorMessage":"boom"}')
    with tempfile.TemporaryDirectory() as d:
        out_csv = os.path.join(d, "out.csv")
        rc, out = run(ci.export, ENV, out_csv, ["de"], ["items"])
        assert rc == 1, (rc, out)
        assert "INCOMPLETE" in out, out


@case("an unrecognized list-response key warns instead of reading as empty")
def _():
    ci.api = lambda e, m, p, body=None, api_version="v2": (200, {"chains": [{"id": 1}]})
    rc, out = run(ci.fetch_all, ENV, "/admin/x")
    assert "unrecognized key" in out, out


# --- the write path -----------------------------------------------------------------

@case("the snapshot covers ALL objects and lands before the FIRST put")
def _():
    # This shipped as a real bug: a single pass snapshotted from inside the write loop,
    # so it captured 1 object while the run replaced N — `restore` then silently undid
    # 1 of N. A 1-object test cannot see it; this one uses three.
    order, snapped = [], {}

    def api(env, method, path, body=None, api_version="v2", **kw):
        order.append(method)
        if method == "GET":
            return 200, dict(ITEM, sku=path.rsplit("/", 1)[-1])
        return 204, {}

    def fake_snapshot(p, objects):
        order.append("SNAPSHOT")
        snapped["n"] = len(objects)
        return "snap.json"

    ci.api, ci._snapshot = api, fake_snapshot
    rc, out = imp([["items", "a", "", "name", "", "Sword", "Schwert"],
                   ["items", "b", "", "name", "", "Sword", "Schwert"],
                   ["items", "c", "", "name", "", "Sword", "Schwert"]],
                  write=True, snapshot=True, verify=False)
    assert rc == 0, out
    assert snapped.get("n") == 3, snapped
    assert order.index("SNAPSHOT") < order.index("PUT"), order


@case("the snapshot holds nested members as they were, not as they will be")
def _():
    # _merge_nested returns a new dict with translations already in its members, and the
    # snapshot was taken from that copy — so `restore` put a nested translation BACK
    # instead of removing it. The PUT returned 204 and the rollback looked clean.
    snapped = {}

    def api(env, method, path, body=None, api_version="v2", **kw):
        if method == "GET":
            return 200, json.loads(json.dumps(CHAIN))
        return 204, {}

    def fake_snapshot(p, objects):
        snapped["objects"] = json.loads(json.dumps(objects))
        return "snap.json"

    ci.api, ci._snapshot = api, fake_snapshot
    rc, out = imp([["reward_chain", "c1", "12", "step_name", "", "Step", "Schritt"]],
                  write=True, snapshot=True, verify=False)
    assert rc == 0, out
    step = snapped["objects"][0]["object"]["steps"][0]
    assert step["name"] == {"en": "Step"}, (
        f"snapshot captured the POST-merge step name {step['name']} — rollback would "
        f"re-apply the translation instead of removing it")


@case("fill-only never overwrites an existing translation")
def _():
    log = []
    stub(obj=dict(ITEM, name={"en": "Sword", "de": "Klinge"}), log=log)
    rc, out = imp([["items", "x", "", "name", "", "Sword", "Schwert"]])
    assert rc == 0, out
    assert "0 translation(s) would change" in out, out
    stub(obj=dict(ITEM, name={"en": "Sword", "de": "Klinge"}))
    rc, out = imp([["items", "x", "", "name", "", "Sword", "Schwert"]], overwrite=True)
    assert "1 translation(s) would change" in out, out


@case("the put body passes every read field back (no allowlist)")
def _():
    log = []
    stub(log=log)
    rc, out = imp([["items", "x", "", "name", "", "Sword", "Schwert"]],
                  write=True, verify=False)
    assert rc == 0, out
    body = [c[2] for c in log if c[0] == "PUT"][0]
    for keep in ("image_url", "groups", "inventory_options"):
        assert keep in body, (keep, sorted(body))
    assert body["name"]["de"] == "Schwert", body["name"]
    assert "item_id" not in body, "server-derived field sent back"


@case("the backup CSV carries a source column, so it can be re-imported")
def _():
    # It promised to be "re-importable on its own" in three places but was written with
    # target locales only, and `_cols` requires a source plus at least one target — so
    # a single-locale backup was refused by the command it exists to feed.
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "b.csv")
        bak = ci._Backup(path, ["en", "de"], source="en")
        bak.add("items", "x", ["name"], {"name": {"en": "Gems", "de": "Edelsteine"}})
        bak.close()
        cols, rows = ci._read_csv(path)
        src, targets = ci._cols(cols, path)          # would sys.exit if unimportable
        assert src == "en" and targets == ["de"], (src, targets)
        assert rows[0]["en"] == "Gems" and rows[0]["de"] == "Edelsteine", rows


@case("fill refuses to pick between two translations for one cell")
def _():
    # Entries are keyed by address, so a duplicate used to collapse with the last one
    # winning and nothing said — in the one input a model writes.
    import json as _json
    dup = _json.dumps([{"entity": "items", "id": "x", "field": "name", "translation": "Schwert"},
                       {"entity": "items", "id": "x", "field": "name", "translation": "Klinge"}])
    entries, problems = ci._parse_fill(dup, "de")
    assert entries == {}, entries
    assert problems and "two different translations" in problems[0], problems
    same = _json.dumps([{"entity": "items", "id": "x", "field": "name", "translation": "Schwert"}] * 2)
    entries, problems = ci._parse_fill(same, "de")
    assert len(entries) == 1 and not problems, (entries, problems)


@case("a game-key price with no `amount` does not crash the shaping step")
def _():
    # The top-level `prices` was guarded for this; unit_items[].prices was not, so a
    # DRM price without an amount raised KeyError mid-write.
    out = ci._shape({"unit_items": [{"sku": "k", "prices": [{"currency": "USD"}]}]},
                    ci.ENTITIES["game"])
    assert out["unit_items"][0]["prices"] == [{"currency": "USD"}], out
    out = ci._shape({"unit_items": [{"sku": "k", "prices": [{"amount": "5"}]}]},
                    ci.ENTITIES["game"])
    assert out["unit_items"][0]["prices"][0]["amount"] == 5.0, out


@case("a chain's is_enabled is never invented, and never flipped")
def _():
    # Defaulting it to True would ENABLE a chain whose read omitted the flag — the one
    # action the skill promises it never takes.
    for ent in ("daily_chain", "offer_chain"):
        assert "is_enabled" not in ci._shape({}, ci.ENTITIES[ent]), ent
        assert ci._shape({"is_enabled": False}, ci.ENTITIES[ent])["is_enabled"] is False
        assert ci._shape({"is_enabled": True}, ci.ENTITIES[ent])["is_enabled"] is True


@case("an unknown locale column refuses before any request")
def _():
    log = []
    stub(log=log)
    rc, out = imp([["items", "x", "", "name", "", "Sword", "x"]],
                  header=["entity", "id", "subid", "field", "context", "en", "pt-PT"],
                  write=True)
    assert rc == 1, out
    assert not log, log


def main():
    failed = []
    for name, fn in _results:
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            failed.append(name)
            print(f"  FAIL {name}\n         {str(e)[:400]}")
        except Exception as e:
            failed.append(name)
            print(f"  ERR  {name}\n         {type(e).__name__}: {str(e)[:400]}")
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
