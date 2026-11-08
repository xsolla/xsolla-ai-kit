"""Small file and entrypoint helpers; command mocks and assertions stay in tests."""

import contextlib
import copy
import io
import json
import sys
from collections.abc import Callable
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import quests_versions  # noqa: E402

# What the CDN serves in tests: no network. 0.2.10 is the newest stable release here; theme
# settings exist where the defaults carry themeId.
FAKE_QUESTS_RELEASES = {
    "0.1.5": {"layout": {}, "maxQuests": 3, "translations": {}},
    "0.1.12": {"layout": {}, "maxQuests": 3, "translations": {}},
    "0.2.7": {"layout": {}, "maxQuests": 3, "themeId": "", "translations": {}},
    "0.2.7-qp-3256.0": {"layout": {}, "maxQuests": 3, "themeId": "", "translations": {}},
    "0.2.10": {"layout": {}, "maxQuests": 3, "themeId": "", "translations": {}},
    "0.2.10-qp-3256.0": {"layout": {}, "maxQuests": 3, "themeId": "", "translations": {}},
}
FAKE_QUESTS_LATEST = "0.2.10"


def fake_quests_cdn(version: str) -> dict | None:
    data = FAKE_QUESTS_RELEASES.get(version)
    return {"defaultData": dict(data), "resources": {"localizedValues": {}}} if data is not None else None


quests_versions.use_fetcher(fake_quests_cdn)


def capture_main(main: Callable[[], int], argv: list[str]) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        mock.patch.object(sys, "argv", argv),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        code = main()
    return code, stdout.getvalue(), stderr.getvalue()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def block_operations_brief(
    operations: list[dict], *, merchant_id: int, project_id: int, slug: str,
) -> dict:
    project = {"merchant_id": merchant_id, "project_id": project_id}
    return {
        "version": 1, "project": project, "site": {"slug": slug},
        "block_operations": copy.deepcopy(operations),
    }
