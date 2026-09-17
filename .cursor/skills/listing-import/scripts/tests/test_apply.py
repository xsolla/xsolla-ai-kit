"""Tests for the write path.

The CLI caller and the image fetcher are injected, so every one of these runs
offline and against no sandbox project. That is the point: the guards on a
write path are exactly the thing you cannot afford to test only by trying it.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from xsolla_listing_import import apply as applier


def ok(body=None):
    return {"cmd": [], "code": 0, "stdout": json.dumps({"data": body or {}}),
            "stderr": ""}


def fail(msg="boom", code=1):
    return {"cmd": [], "code": code, "stdout": "", "stderr": msg}


class FakeCli(object):
    """Records calls and answers from a scripted queue."""

    def __init__(self, answers=None, default=None):
        self.calls = []
        self.answers = dict(answers or {})
        self.default = default or ok()

    def __call__(self, product, action, args, timeout=120):
        if (product, action) not in applier.ALLOWED:
            raise applier.Refused("%s %s not allowed" % (product, action))
        self.calls.append((product, action, list(args)))
        answer = self.answers.get((product, action), self.default)
        return answer(args) if callable(answer) else answer

    def actions(self):
        return ["%s %s" % (p, a) for p, a, _ in self.calls]


def plan_with(*ops, **kw):
    out = {"operations": list(ops), "catalog_operations": kw.get("catalog", []),
           "catalog_warnings": []}
    return out


def loc_op(step=1, localized_id="L:abc", value="<h3>T</h3>"):
    return {"step": step, "kind": "localization", "field": "title",
            "module": "leadGameSales", "block_id": "b1", "page_id": "p1",
            "path": ["values", "title"], "localized_id": localized_id,
            "value": value, "confidence": "schema"}


def asset_op(step=1, path=None):
    return {"step": step, "kind": "asset", "field": "key_art",
            "module": "leadGameSales", "block_id": "b1", "page_id": "p1",
            "path": path or ["values", "background", "img"],
            "source_url": "https://img.test/a.jpg", "confidence": "confirmed"}


def patch_op(step=1, value=True):
    return {"step": step, "kind": "patch", "field": "key_art",
            "module": "leadGameSales", "block_id": "b1", "page_id": "p1",
            "path": ["values", "background", "enable"], "value": value,
            "confidence": "confirmed"}


class TestTheConfirmationGate(unittest.TestCase):
    """--yes is the whole gate; a forgotten flag must cost nothing."""

    def test_a_rehearsal_invokes_nothing(self):
        cli = FakeCli()
        out = applier.apply_plan(plan_with(loc_op(), asset_op()), "s", call=cli,
                                 fetch=lambda u, d: "/tmp/x.jpg")
        self.assertEqual(cli.calls, [])
        self.assertFalse(out["confirmed"])
        self.assertTrue(out["commands"])

    def test_a_rehearsal_takes_no_backup_either(self):
        cli = FakeCli()
        out = applier.apply_plan(plan_with(loc_op()), "s", call=cli)
        self.assertIsNone(out["backup"])
        self.assertNotIn("shopbuilder get-structure", cli.actions())

    def test_confirmed_invokes(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(loc_op()), "s", confirmed=True, call=cli,
                               backup_dir=d)
        self.assertIn("shopbuilder update-localization", cli.actions())


class TestBackupHappensFirst(unittest.TestCase):
    """A run that cannot be undone should not begin."""

    def test_backup_precedes_every_write(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(loc_op()), "s", confirmed=True, call=cli,
                               backup_dir=d)
        actions = cli.actions()
        self.assertEqual(actions[0], "shopbuilder get-structure")
        self.assertEqual(actions[1], "shopbuilder get-localization")
        self.assertLess(actions.index("shopbuilder get-localization"),
                        actions.index("shopbuilder update-localization"))

    def test_both_files_land_on_disk(self):
        cli = FakeCli(default=ok({"pages": []}))
        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with(), "s", confirmed=True, call=cli,
                                     backup_dir=d)
            for path in out["backup"].values():
                self.assertTrue(os.path.exists(path), path)

    def test_a_failed_backup_stops_the_run_before_any_write(self):
        cli = FakeCli(answers={("shopbuilder", "get-structure"): fail("401")})
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(applier.Refused) as caught:
                applier.apply_plan(plan_with(loc_op()), "s", confirmed=True,
                                   call=cli, backup_dir=d)
        self.assertIn("not writing without one", str(caught.exception))
        self.assertNotIn("shopbuilder update-localization", cli.actions())

    def test_a_backup_with_no_json_body_also_stops(self):
        cli = FakeCli(answers={("shopbuilder", "get-localization"):
                               {"cmd": [], "code": 0, "stdout": "not json",
                                "stderr": ""}})
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(applier.Refused):
                applier.apply_plan(plan_with(loc_op()), "s", confirmed=True,
                                   call=cli, backup_dir=d)


class TestTheAllowlist(unittest.TestCase):
    """"Never publish" should be structural, not a line in a README."""

    def test_publish_like_commands_are_not_in_the_allowlist(self):
        for action in ("delete-website", "delete-block", "delete-asset",
                       "enable-preview", "preview-link", "set-landing-type"):
            self.assertNotIn(("shopbuilder", action), applier.ALLOWED, action)

    def test_calling_one_raises_refused(self):
        with self.assertRaises(applier.Refused):
            applier.cli_call("shopbuilder", "delete-website", [])

    def test_the_allowlist_is_only_reads_and_additive_writes(self):
        for _product, action in applier.ALLOWED:
            self.assertFalse(action.startswith("delete"), action)
            self.assertNotIn("publish", action, action)


class TestLocalizationRefusals(unittest.TestCase):
    """It will not invent an L: id."""

    def test_a_missing_id_is_skipped_not_guessed(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with(loc_op(localized_id=None)), "s",
                                     confirmed=True, call=cli, backup_dir=d)
        self.assertEqual(len(out["skipped"]), 1)
        self.assertIn("nothing to write to", out["skipped"][0]["reason"])
        self.assertNotIn("shopbuilder update-localization", cli.actions())

    def test_the_write_carries_the_id_the_block_gave(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(loc_op(localized_id="L:real")), "s",
                               confirmed=True, call=cli, backup_dir=d)
        call = [c for c in cli.calls if c[1] == "update-localization"][0]
        data = json.loads(call[2][call[2].index("--data") + 1])
        self.assertEqual(data["id"], "L:real")
        self.assertEqual(data["locale"], "en-US")

    def test_a_non_default_locale_is_honoured(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(loc_op()), "s", locale="ja-JP",
                               confirmed=True, call=cli, backup_dir=d)
        call = [c for c in cli.calls if c[1] == "update-localization"][0]
        data = json.loads(call[2][call[2].index("--data") + 1])
        self.assertEqual(data["locale"], "ja-JP")


class TestOverflowRefusal(unittest.TestCase):

    def test_it_will_not_invent_a_component_id(self):
        op = {"step": 1, "kind": "overflow", "field": "genres+tags",
              "module": "description", "block_id": "b", "page_id": "p",
              "path": ["values", "components"], "value": "<p>x</p>",
              "confidence": "schema"}
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with(op), "s", confirmed=True, call=cli,
                                     backup_dir=d)
        self.assertEqual(len(out["skipped"]), 1)
        self.assertIn("will not invent", out["skipped"][0]["reason"])
        self.assertNotIn("shopbuilder update-block", cli.actions())


class TestReadBack(unittest.TestCase):
    """A patch to a path that does not exist answers ok:true and does nothing."""

    def _run(self, block_after):
        cli = FakeCli(answers={("shopbuilder", "get-block"): ok(block_after)})
        with tempfile.TemporaryDirectory() as d:
            return cli, applier.apply_plan(plan_with(patch_op(value=True)), "s",
                                           confirmed=True, call=cli, backup_dir=d)

    def test_a_confirmed_value_counts_as_applied(self):
        _cli, out = self._run({"values": {"background": {"enable": True}}})
        self.assertEqual(len(out["performed"]), 1)
        self.assertEqual(out["performed"][0]["verified"], "confirmed")
        self.assertEqual(out["failed"], [])

    def test_a_silent_no_op_is_reported_as_a_failure(self):
        _cli, out = self._run({"values": {}})
        self.assertEqual(out["performed"], [])
        self.assertEqual(len(out["failed"]), 1)
        self.assertIn("accepted and changed nothing", out["failed"][0]["reason"])

    def test_a_wrong_value_is_reported(self):
        _cli, out = self._run({"values": {"background": {"enable": False}}})
        self.assertEqual(len(out["failed"]), 1)
        self.assertIn("expected", out["failed"][0]["reason"])

    def test_every_write_is_read_back_not_a_sample(self):
        cli = FakeCli(answers={("shopbuilder", "get-block"):
                               ok({"values": {"background": {"enable": True}}})})
        ops = [patch_op(step=i, value=True) for i in range(1, 4)]
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(*ops), "s", confirmed=True, call=cli,
                               backup_dir=d)
        self.assertEqual(cli.actions().count("shopbuilder get-block"), 3)


class TestAssets(unittest.TestCase):
    """upload-asset takes a local file; a source URL must never be patched in."""

    def test_the_cdn_url_is_patched_not_the_source(self):
        cli = FakeCli(answers={
            ("shopbuilder", "upload-asset"): ok({"url": "https://cdn.test/x.jpg"}),
            ("shopbuilder", "get-block"): ok(
                {"values": {"background": {"img": "https://cdn.test/x.jpg"}}}),
        })
        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with(asset_op()), "s", confirmed=True,
                                     call=cli, backup_dir=d,
                                     fetch=lambda u, w: os.path.join(w, "a.jpg"),
                                     workdir=d)
        patch = [c for c in cli.calls if c[1] == "update-block"][0]
        data = json.loads(patch[2][patch[2].index("--data") + 1])
        written = data["r1"]["patches"][0]["value"]
        self.assertEqual(written, "https://cdn.test/x.jpg")
        self.assertNotIn("img.test", written)
        self.assertEqual(len(out["performed"]), 1)

    def test_upload_before_patch(self):
        cli = FakeCli(answers={
            ("shopbuilder", "upload-asset"): ok({"url": "https://cdn.test/x.jpg"}),
            ("shopbuilder", "get-block"): ok(
                {"values": {"background": {"img": "https://cdn.test/x.jpg"}}}),
        })
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(asset_op()), "s", confirmed=True, call=cli,
                               backup_dir=d, fetch=lambda u, w: "/tmp/a.jpg",
                               workdir=d)
        actions = cli.actions()
        self.assertLess(actions.index("shopbuilder upload-asset"),
                        actions.index("shopbuilder update-block"))

    def test_a_failed_fetch_is_reported_and_nothing_is_patched(self):
        cli = FakeCli()

        def boom(url, directory):
            raise applier.Refused("over 10 MB")

        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with(asset_op()), "s", confirmed=True,
                                     call=cli, backup_dir=d, fetch=boom, workdir=d)
        self.assertEqual(len(out["failed"]), 1)
        self.assertIn("fetch failed", out["failed"][0]["reason"])
        self.assertNotIn("shopbuilder update-block", cli.actions())

    def test_an_upload_returning_no_url_does_not_patch(self):
        cli = FakeCli(answers={("shopbuilder", "upload-asset"): ok({})})
        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with(asset_op()), "s", confirmed=True,
                                     call=cli, backup_dir=d,
                                     fetch=lambda u, w: "/tmp/a.jpg", workdir=d)
        self.assertIn("no url", out["failed"][0]["reason"])
        self.assertNotIn("shopbuilder update-block", cli.actions())

    def test_a_non_http_image_url_is_refused_by_the_real_fetcher(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(applier.Refused):
                applier.fetch_image("file:///etc/passwd", d)
            with self.assertRaises(applier.Refused):
                applier.fetch_image("javascript:alert(1)", d)


class TestOrdering(unittest.TestCase):
    """Localization before the image patches: an unresolved L: ref 500s."""

    def test_localization_precedes_asset_writes(self):
        cli = FakeCli(answers={
            ("shopbuilder", "upload-asset"): ok({"url": "https://cdn.test/x.jpg"}),
            ("shopbuilder", "get-block"): ok(
                {"values": {"background": {"img": "https://cdn.test/x.jpg"}}}),
        })
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(loc_op(step=1), asset_op(step=2)), "s",
                               confirmed=True, call=cli, backup_dir=d,
                               fetch=lambda u, w: "/tmp/a.jpg", workdir=d)
        actions = cli.actions()
        self.assertLess(actions.index("shopbuilder update-localization"),
                        actions.index("shopbuilder upload-asset"))


class TestCatalog(unittest.TestCase):

    def _item(self, sku="ios_gems", priced=True):
        return {"kind": "catalog", "entity": "virtual_item", "sku": sku,
                "name": {"en": "Gems"}, "description": {"en": "d"},
                "prices": [{"amount": 0.99, "currency": "USD",
                            "is_default": True, "is_enabled": True}] if priced else [],
                "groups": ["imported_listing"], "is_enabled": priced,
                "is_show_in_store": priced, "needs_review": True,
                "review_reason": "r"}

    def test_the_group_is_created_once_before_the_items(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(catalog=[self._item("a"), self._item("b")]),
                               "s", confirmed=True, call=cli, backup_dir=d)
        actions = cli.actions()
        self.assertEqual(actions.count("catalog admin-create-group"), 1)
        self.assertLess(actions.index("catalog admin-create-group"),
                        actions.index("catalog create-items"))

    def test_an_unpriced_item_is_created_without_enable_flags(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            applier.apply_plan(plan_with(catalog=[self._item(priced=False)]), "s",
                               confirmed=True, call=cli, backup_dir=d)
        args = [c for c in cli.calls if c[1] == "create-items"][0][2]
        self.assertNotIn("--is-enabled", args)
        self.assertNotIn("--prices", args)

    def test_a_failed_create_is_reported(self):
        cli = FakeCli(answers={("catalog", "create-items"): fail("409 exists")})
        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with(catalog=[self._item()]), "s",
                                     confirmed=True, call=cli, backup_dir=d)
        self.assertEqual(len(out["failed"]), 1)
        self.assertIn("409", out["failed"][0]["reason"])


class TestUnknownOperation(unittest.TestCase):

    def test_an_unrecognised_kind_is_skipped_not_executed(self):
        cli = FakeCli()
        with tempfile.TemporaryDirectory() as d:
            out = applier.apply_plan(plan_with({"step": 1, "kind": "teleport",
                                                "field": "x"}), "s",
                                     confirmed=True, call=cli, backup_dir=d)
        self.assertIn("unknown operation kind", out["skipped"][0]["reason"])
        self.assertEqual([a for a in cli.actions() if not a.startswith("shopbuilder get")],
                         [])


if __name__ == "__main__":
    unittest.main()


class TestApplyPlanCli(unittest.TestCase):
    """The entry point's own gate and exit codes."""

    def setUp(self):
        import io
        import apply_plan
        self.apply_plan = apply_plan
        self.io = io
        self.tmp = tempfile.mkdtemp()

    def write(self, name, obj):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return path

    def run_cli(self, argv):
        from contextlib import redirect_stdout
        buf = self.io.StringIO()
        with redirect_stdout(buf):
            code = self.apply_plan.main(argv)
        return code, buf.getvalue()

    def test_a_plan_with_blockers_is_refused_with_exit_two(self):
        path = self.write("p.json", {
            "blockers": [{"path": "rights_confirmed", "expected": "true",
                          "got": "not confirmed"}],
            "plan": plan_with(loc_op())})
        code, out = self.run_cli(["--plan", path, "--slug", "s"])
        self.assertEqual(code, self.apply_plan.EXIT_USAGE)
        self.assertIn("REFUSED", out)
        self.assertIn("Nothing was sent", out)

    def test_a_rehearsal_says_so_and_exits_on_skips(self):
        path = self.write("p.json", {"plan": plan_with(loc_op(localized_id=None))})
        code, out = self.run_cli(["--plan", path, "--slug", "s"])
        self.assertIn("REHEARSAL", out)
        self.assertIn("Add --yes to write", out)
        self.assertEqual(code, self.apply_plan.EXIT_PROBLEMS)

    def test_a_clean_rehearsal_exits_zero(self):
        path = self.write("p.json", {"plan": plan_with(loc_op())})
        code, _out = self.run_cli(["--plan", path, "--slug", "s"])
        self.assertEqual(code, self.apply_plan.EXIT_CLEAN)

    def test_every_run_prints_the_never_publish_line(self):
        path = self.write("p.json", {"plan": plan_with(loc_op())})
        _code, out = self.run_cli(["--plan", path, "--slug", "s"])
        self.assertIn("Never publish", out)

    def test_a_file_that_is_not_a_plan_exits_two(self):
        path = self.write("p.json", {"something": "else"})
        code, _out = self.run_cli(["--plan", path, "--slug", "s"])
        self.assertEqual(code, self.apply_plan.EXIT_USAGE)

    def test_a_bare_plan_without_the_envelope_is_accepted(self):
        path = self.write("p.json", plan_with(loc_op()))
        code, _out = self.run_cli(["--plan", path, "--slug", "s"])
        self.assertEqual(code, self.apply_plan.EXIT_CLEAN)

    def test_a_missing_file_exits_two(self):
        code, _out = self.run_cli(["--plan", os.path.join(self.tmp, "no.json"),
                                   "--slug", "s"])
        self.assertEqual(code, self.apply_plan.EXIT_USAGE)
