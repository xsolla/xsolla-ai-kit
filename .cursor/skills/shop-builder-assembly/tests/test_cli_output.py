"""The CLI writes UTF-8; Windows Python decodes pipes with the ANSI code page."""

from __future__ import annotations

import contextlib
import importlib.util
import locale
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_for_cli_output_tests", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCRIPTS = {name: load_script(name) for name in ("apply_plan", "backup_shop", "preflight")}

# "Космос" encodes to bytes that include 0x81, which cp1252 cannot decode.
UNICODE_TEXT = "Космос — Café"


@contextlib.contextmanager
def ansi_code_page_default():
    """Make cp1252 Python's default subprocess text encoding, as on a Western Windows PC."""
    with contextlib.ExitStack() as stack:
        if hasattr(locale, "getencoding"):  # Python 3.11 and later
            stack.enter_context(mock.patch("locale.getencoding", return_value="cp1252"))
        try:
            import _bootlocale  # Python 3.9 and earlier
        except ImportError:
            pass
        else:
            stack.enter_context(
                mock.patch.object(_bootlocale, "getpreferredencoding", return_value="cp1252")
            )
        yield


@unittest.skipIf(os.name == "nt", "the fake CLI is a POSIX script")
class CliOutputDecodingTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.bin = Path(directory.name)
        path = mock.patch.dict(
            os.environ, {"PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", "")}
        )
        path.start()
        self.addCleanup(path.stop)

    def fake_cli(self, stdout: str = "", stderr: str = "", exit_code: int = 0) -> None:
        script = self.bin / "xsolla"
        script.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            f"sys.stdout.buffer.write({stdout.encode('utf-8')!r})\n"
            f"sys.stderr.buffer.write({stderr.encode('utf-8')!r})\n"
            f"sys.exit({exit_code})\n",
            encoding="utf-8",
        )
        script.chmod(0o755)

    def test_cyrillic_and_accented_output_decodes(self) -> None:
        self.fake_cli(stdout='{"ok": true, "data": {"name": "' + UNICODE_TEXT + '"}}')
        for name, script in SCRIPTS.items():
            with self.subTest(name), ansi_code_page_default():
                with mock.patch.object(
                    script.subprocess, "run", wraps=subprocess.run
                ) as run:
                    self.assertEqual(
                        {"ok": True, "data": {"name": UNICODE_TEXT}},
                        script.run_json("shopbuilder", "get-structure"),
                    )
                self.assertEqual("utf-8", run.call_args.kwargs["encoding"])
                self.assertNotIn("errors", run.call_args.kwargs)

    def test_cyrillic_and_accented_error_detail_decodes(self) -> None:
        self.fake_cli(stderr=f"landing {UNICODE_TEXT} was not found", exit_code=40)
        for name, script in SCRIPTS.items():
            with self.subTest(name), ansi_code_page_default():
                with self.assertRaisesRegex(RuntimeError, UNICODE_TEXT):
                    script.run_json("shopbuilder", "get-landing", "--slug", "shop")


class CliOutputShapeTests(unittest.TestCase):
    def test_missing_or_invalid_stdout_raises_runtime_error_with_stderr(self) -> None:
        stderr = "the stdout reader thread failed"
        for stdout in (None, "", " \n", "not json"):
            result = mock.Mock(returncode=0, stdout=stdout, stderr=stderr)
            for name, script in SCRIPTS.items():
                with self.subTest(script=name, stdout=stdout):
                    with mock.patch.object(script.subprocess, "run", return_value=result):
                        with self.assertRaisesRegex(RuntimeError, stderr):
                            script.run_json("shopbuilder", "list-websites")

    def test_failed_command_with_no_output_raises_runtime_error(self) -> None:
        result = mock.Mock(returncode=1, stdout=None, stderr=None)
        for name, script in SCRIPTS.items():
            with self.subTest(name):
                with mock.patch.object(script.subprocess, "run", return_value=result):
                    with self.assertRaisesRegex(RuntimeError, "exit code 1"):
                        script.run_json("config", "list")

    def test_preflight_child_writes_and_is_read_as_utf8(self) -> None:
        apply_plan = SCRIPTS["apply_plan"]
        succeeded = mock.Mock(returncode=0, stdout="{}", stderr="")
        with mock.patch.object(apply_plan.subprocess, "run", return_value=succeeded) as run:
            apply_plan.run_preflight(Path("brief.json"), None)
        self.assertEqual([sys.executable, "-X", "utf8"], run.call_args.args[0][:3])
        self.assertEqual("utf-8", run.call_args.kwargs["encoding"])
        self.assertNotIn("errors", run.call_args.kwargs)

    def test_preflight_failure_without_output_is_a_runtime_error(self) -> None:
        apply_plan = SCRIPTS["apply_plan"]
        failed = mock.Mock(returncode=1, stdout=None, stderr=None)
        with mock.patch.object(apply_plan.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "preflight failed"):
                apply_plan.run_preflight(Path("brief.json"), None)


if __name__ == "__main__":
    unittest.main()
