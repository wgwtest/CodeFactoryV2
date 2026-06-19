from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_BASH = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"
POWERSHELL = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"


def _bash_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = resolved.as_posix().split(":", 1)[1]
    return f"/{drive}{rest}"


def _settings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _powershell_literal(value: Path | str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    for name in [
        "CF_API_HOST",
        "CF_API_PORT",
        "CF_DEV_BRANCH_OVERRIDE",
        "CODEFACTORY_LOCAL_DIFY_ENV",
        "CODEFACTORY_P3_DIFY_API_KEY",
        "CODEFACTORY_P3_DIFY_BASE_URL",
        "CODEFACTORY_P3_DIFY_TIMEOUT_SECONDS",
        "CODEFACTORY_P3_DIFY_WORKFLOW_ID",
        "CODEFACTORY_P3_SCOPED_DIFY_API_KEY",
        "CODEFACTORY_P3_SCOPED_DIFY_BASE_URL",
        "CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS",
        "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID",
        "VITE_API_PROXY_TARGET",
        "VITE_DEFAULT_ROUTE",
        "VITE_DEV_API_PROXY_TARGET",
        "VITE_WEB_HOST",
        "VITE_WEB_PORT",
    ]:
        env.pop(name, None)
    return env


def test_dev_ports_dify_workflow_ids_match_dify_handoff_contract() -> None:
    settings = _settings(REPO_ROOT / "config" / "dev-ports.env")

    assert settings["CODEFACTORY_P3_DIFY_WORKFLOW_ID"] == "587ab682-81d2-40d4-b4ee-047849455b5f"
    assert settings["CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID"] == "1b1d17a4-cb0f-4c9c-b59b-8d6ba76f22ff"


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


def test_load_dev_ports_sources_repo_local_dify_env_before_user_env(tmp_path: Path) -> None:
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
                "CODEFACTORY_P3_DIFY_BASE_URL=http://shared.example/v1",
                "CODEFACTORY_P3_DIFY_WORKFLOW_ID=shared-conversion-workflow",
                "CODEFACTORY_P3_DIFY_TIMEOUT_SECONDS=520",
                "CODEFACTORY_P3_SCOPED_DIFY_BASE_URL=http://shared.example/v1",
                "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=shared-scoped-workflow",
                "CODEFACTORY_P3_SCOPED_DIFY_TIMEOUT_SECONDS=180",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workdir / "config" / "dify.local.env").write_text(
        "\n".join(
            [
                "CODEFACTORY_P3_DIFY_BASE_URL=http://repo-local.example/v1",
                "CODEFACTORY_P3_DIFY_API_KEY=repo-local-conversion-key",
                "CODEFACTORY_P3_DIFY_WORKFLOW_ID=repo-local-conversion-workflow",
                "CODEFACTORY_P3_SCOPED_DIFY_API_KEY=repo-local-scoped-key",
                "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=repo-local-scoped-workflow",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    machine_env = tmp_path / "dify.local.env"
    machine_env.write_text(
        "\n".join(
            [
                "CODEFACTORY_P3_DIFY_WORKFLOW_ID=user-conversion-workflow",
                "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=user-scoped-workflow",
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
            "\"conversion_base=$CODEFACTORY_P3_DIFY_BASE_URL\" "
            "\"conversion_workflow=$CODEFACTORY_P3_DIFY_WORKFLOW_ID\" "
            "\"conversion_key=$CODEFACTORY_P3_DIFY_API_KEY\" "
            "\"scoped_workflow=$CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID\" "
            "\"scoped_key=$CODEFACTORY_P3_SCOPED_DIFY_API_KEY\"",
        ],
        cwd=workdir,
        env=env,
        text=True,
    )

    assert "conversion_base=http://repo-local.example/v1" in output
    assert "conversion_workflow=user-conversion-workflow" in output
    assert "conversion_key=repo-local-conversion-key" in output
    assert "scoped_workflow=user-scoped-workflow" in output
    assert "scoped_key=repo-local-scoped-key" in output


def test_load_dev_ports_powershell_sources_versioned_config_machine_secrets_and_branch_ports(tmp_path: Path) -> None:
    if not POWERSHELL.exists():
        pytest.skip("Windows PowerShell is not available")

    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "scripts").mkdir()
    (workdir / "config").mkdir()
    shutil.copy(REPO_ROOT / "scripts" / "load_dev_ports.ps1", workdir / "scripts" / "load_dev_ports.ps1")

    (workdir / "config" / "dev-ports.env").write_text(
        "\n".join(
            [
                "MAIN_API_PORT=8020",
                "MAIN_WEB_PORT=5173",
                "MAIN_DEFAULT_ROUTE=/documents",
                "FEAT_P3_REQUIREMENT_TO_DESIGN_CONVERSION_API_PORT=8031",
                "FEAT_P3_REQUIREMENT_TO_DESIGN_CONVERSION_WEB_PORT=5175",
                "FEAT_P3_REQUIREMENT_TO_DESIGN_CONVERSION_DEFAULT_ROUTE=/p3-design-lab",
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

    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"$env:CODEFACTORY_LOCAL_DIFY_ENV = {_powershell_literal(machine_env)}",
            "$env:CF_DEV_BRANCH_OVERRIDE = 'feat/p3-requirement-to-design-conversion'",
            ". .\\scripts\\load_dev_ports.ps1",
            '"api=$env:CF_API_PORT"',
            '"web=$env:VITE_WEB_PORT"',
            '"route=$env:VITE_DEFAULT_ROUTE"',
            '"conversion_workflow=$env:CODEFACTORY_P3_DIFY_WORKFLOW_ID"',
            '"conversion_key=$env:CODEFACTORY_P3_DIFY_API_KEY"',
            '"scoped_workflow=$env:CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID"',
            '"scoped_key=$env:CODEFACTORY_P3_SCOPED_DIFY_API_KEY"',
        ]
    )
    output = subprocess.check_output(
        [
            str(POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=workdir,
        env=_clean_env(),
        text=True,
    )

    assert "api=8031" in output
    assert "web=5175" in output
    assert "route=/p3-design-lab" in output
    assert "conversion_workflow=versioned-conversion-workflow" in output
    assert "conversion_key=fake-conversion-key" in output
    assert "scoped_workflow=versioned-scoped-workflow" in output
    assert "scoped_key=fake-scoped-key" in output


def test_load_dev_ports_powershell_sources_repo_local_dify_env_before_user_env(tmp_path: Path) -> None:
    if not POWERSHELL.exists():
        pytest.skip("Windows PowerShell is not available")

    workdir = tmp_path / "repo"
    workdir.mkdir()
    (workdir / "scripts").mkdir()
    (workdir / "config").mkdir()
    shutil.copy(REPO_ROOT / "scripts" / "load_dev_ports.ps1", workdir / "scripts" / "load_dev_ports.ps1")

    (workdir / "config" / "dev-ports.env").write_text(
        "\n".join(
            [
                "MAIN_API_PORT=8020",
                "MAIN_WEB_PORT=5173",
                "MAIN_DEFAULT_ROUTE=/documents",
                "CODEFACTORY_P3_DIFY_BASE_URL=http://shared.example/v1",
                "CODEFACTORY_P3_DIFY_WORKFLOW_ID=shared-conversion-workflow",
                "CODEFACTORY_P3_SCOPED_DIFY_BASE_URL=http://shared.example/v1",
                "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=shared-scoped-workflow",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (workdir / "config" / "dify.local.env").write_text(
        "\n".join(
            [
                "CODEFACTORY_P3_DIFY_BASE_URL=http://repo-local.example/v1",
                "CODEFACTORY_P3_DIFY_API_KEY=repo-local-conversion-key",
                "CODEFACTORY_P3_DIFY_WORKFLOW_ID=repo-local-conversion-workflow",
                "CODEFACTORY_P3_SCOPED_DIFY_API_KEY=repo-local-scoped-key",
                "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=repo-local-scoped-workflow",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    machine_env = tmp_path / "dify.local.env"
    machine_env.write_text(
        "\n".join(
            [
                "CODEFACTORY_P3_DIFY_WORKFLOW_ID=user-conversion-workflow",
                "CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID=user-scoped-workflow",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    command = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            f"$env:CODEFACTORY_LOCAL_DIFY_ENV = {_powershell_literal(machine_env)}",
            ". .\\scripts\\load_dev_ports.ps1",
            '"conversion_base=$env:CODEFACTORY_P3_DIFY_BASE_URL"',
            '"conversion_workflow=$env:CODEFACTORY_P3_DIFY_WORKFLOW_ID"',
            '"conversion_key=$env:CODEFACTORY_P3_DIFY_API_KEY"',
            '"scoped_workflow=$env:CODEFACTORY_P3_SCOPED_DIFY_WORKFLOW_ID"',
            '"scoped_key=$env:CODEFACTORY_P3_SCOPED_DIFY_API_KEY"',
        ]
    )
    output = subprocess.check_output(
        [
            str(POWERSHELL),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=workdir,
        env=_clean_env(),
        text=True,
    )

    assert "conversion_base=http://repo-local.example/v1" in output
    assert "conversion_workflow=user-conversion-workflow" in output
    assert "conversion_key=repo-local-conversion-key" in output
    assert "scoped_workflow=user-scoped-workflow" in output
    assert "scoped_key=repo-local-scoped-key" in output


def test_local_dify_override_files_are_git_ignored() -> None:
    paths = [
        "dify.local.env",
        "config/dify.local.env",
        ".codefactory/dify.local.env",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        cwd=REPO_ROOT,
        input=("\n".join(paths) + "\n").encode(),
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert set(result.stdout.decode().splitlines()) == set(paths)
