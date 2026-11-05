"""Small file and entrypoint helpers; command mocks and assertions stay in tests."""

import contextlib
import copy
import io
import json
import sys
from collections.abc import Callable
from pathlib import Path
from unittest import mock


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
    legacy_acknowledgment: bool = False,
) -> dict:
    project = {"merchant_id": merchant_id, "project_id": project_id, "environment": "test"}
    if legacy_acknowledgment:
        project["test_project_acknowledged"] = True
    return {
        "version": 1, "project": project, "site": {"slug": slug},
        "block_operations": copy.deepcopy(operations),
    }


def approved_projects(
    merchant_id: int, project_id: int, *, approved_by: str, approval_reference: str,
) -> dict:
    return {"version": 1, "projects": [{
        "merchant_id": merchant_id, "project_id": project_id,
        "approved_by": approved_by, "approval_reference": approval_reference,
    }]}
