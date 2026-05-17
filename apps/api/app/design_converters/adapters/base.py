from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Protocol

from app.config import REPO_ROOT
from app.design_converters.models import DesignConverterManifest, DesignConverterRunRequest, DesignConverterRunResult


class DesignConverterAdapter(Protocol):
    def run(self, request: DesignConverterRunRequest) -> DesignConverterRunResult:
        ...


def load_design_converter_adapter(
    manifest: DesignConverterManifest,
    *,
    package: Any | None = None,
) -> DesignConverterAdapter:
    module = _load_module(manifest)
    adapter_class = getattr(module, manifest.adapter_class)
    try:
        return adapter_class(manifest=manifest, package=package)
    except TypeError:
        return adapter_class(manifest=manifest)


def _module_name(adapter_module: str) -> str:
    if adapter_module.startswith("app."):
        return adapter_module
    if adapter_module.startswith("adapters."):
        return f"app.design_converters.{adapter_module}"
    return adapter_module


def _load_module(manifest: DesignConverterManifest):
    adapter_module = manifest.adapter_module
    if adapter_module.startswith("app.") or adapter_module.startswith("adapters."):
        return importlib.import_module(_module_name(adapter_module))

    module_path = _plugin_module_path(manifest, adapter_module)
    plugin_package_name = _plugin_package_name(manifest)
    _ensure_plugin_package(plugin_package_name, _plugin_dir(manifest))
    module_name = f"{plugin_package_name}.{adapter_module}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(f"cannot load design converter adapter module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _plugin_module_path(manifest: DesignConverterManifest, adapter_module: str):
    plugin_dir = _plugin_dir(manifest)
    return plugin_dir / f"{adapter_module.replace('.', '/')}.py"


def _plugin_dir(manifest: DesignConverterManifest):
    package_path = Path(manifest.package_path)
    if package_path.is_absolute():
        return package_path
    return REPO_ROOT / package_path


def _plugin_package_name(manifest: DesignConverterManifest) -> str:
    safe_id = "".join(character if character.isalnum() else "_" for character in manifest.converter_id)
    return f"_codefactory_design_converter_{safe_id}"


def _ensure_plugin_package(package_name: str, plugin_dir: Path) -> None:
    package = sys.modules.get(package_name)
    if package is None:
        spec = importlib.util.spec_from_loader(package_name, loader=None, is_package=True)
        package = importlib.util.module_from_spec(spec)
        package.__path__ = [str(plugin_dir)]
        sys.modules[package_name] = package
        return
    package.__path__ = [str(plugin_dir)]
