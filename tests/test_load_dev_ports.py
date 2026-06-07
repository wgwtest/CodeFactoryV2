from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"


def _bash_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":", 1)[1]
    return f"/{drive}{rest}"


def test_load_dev_ports_sources_versioned_config_machine_secrets_and_local_overrides(tmp_path: Path) -> None:
    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "scripts").mkdir()
    (workdir / "config").mkdir()
    shutil.copy(REPO_ROOT / "scripts" / "load_dev_ports.sh", workdir / "scripts" / "load_dev_ports.sh")

    (workdir / "config" / "dev-ports.env").write_text(
        "\n".join(
            [
                "MAIN_API_PORT=8020",
                "MAIN_WEB_PORT=5173",
                "MAIN_DEFAULT_ROUTE=/documents",
                "CODEFACTORY_P3_DIFY_BASE_URL=http://localhost/v1",
                "CODEFACTORY_P3_DIFY_WORKFLOW_ID=versioned-conversion-workflow",
                "CODEFACTORY_P3_DIFY_TIMEOUT_SECONDS=520",
                "CODEFACTORY_P3_SCOPED_DIFY_BASE_URL=http://localhost/v1",
                "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=versioned-scoped-workflow",
                "CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS=180",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workdir / ".env.local").write_text("CF_API_PORT=8999\n", encoding="utf-8")
    machine_env = tmp_path / "dify.local.env"
    machine_env.write_text(
        "\n".join(
            [
                "CODEFACTORY_P3_DIFY_API_KEY=fake-conversion-key",
                "CODEFACTORY_P3_SCOPED_DIFY_API_KEY=fake-scoped-key",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["CODEFACTORY_LOCAL_DIFY_ENV"] = _bash_path(machine_env)
    output = subprocess.check_output(
        [
            str(GIT_BASH),
            "-lc",
            "source scripts/load_dev_ports.sh && "
            "printf '%s\\n' "
            "\"api=$CF_API_PORT\" "
            "\"conversion_workflow=$CODEFACTORY_P3_DIFY_WORKFLOW_ID\" "
            "\"conversion_key=$CODEFACTORY_P3_DIFY_API_KEY\" "
            "\"scoped_workflow=$CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID\" "
            "\"scoped_key=$CODEFACTORY_P3_SCOPED_DIFY_API_KEY\"",
        ],
        cwd=workdir,
        env=env,
        text=True,
    )

    assert "api=8999" in output
    assert "conversion_workflow=versioned-conversion-workflow" in output
    assert "conversion_key=fake-conversion-key" in output
    assert "scoped_workflow=versioned-scoped-workflow" in output
    assert "scoped_key=fake-scoped-key" in output
