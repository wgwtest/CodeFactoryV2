from __future__ import annotations

from functools import lru_cache

from app.design_converters.models import DesignConverterManifest
from app.design_converters.plugin_discovery import DesignConverterPluginDiscovery


class DesignConverterPluginRegistry:
    def __init__(self) -> None:
        discovery_result = DesignConverterPluginDiscovery().discover()
        if discovery_result.errors:
            messages = "; ".join(error.message for error in discovery_result.errors)
            raise ValueError(f"design converter plugin discovery failed: {messages}")
        self._plugins = {item.manifest.converter_id: item.manifest for item in discovery_result.plugins}
        self._aliases = {
            alias: item.manifest.converter_id
            for item in discovery_result.plugins
            for alias in item.manifest.aliases
        }

    def list_converters(self) -> list[DesignConverterManifest]:
        return sorted(self._plugins.values(), key=lambda item: (item.priority, item.converter_id))

    def default_converter(self) -> DesignConverterManifest:
        active_converters = [
            converter
            for converter in self.list_converters()
            if str(converter.status or "").lower() in {"active", "available"}
        ]
        converters = active_converters or self.list_converters()
        if not converters:
            raise ValueError("no P3 design converters available")
        return converters[0]

    def get(self, converter_id: str) -> DesignConverterManifest | None:
        return self._plugins.get(self._normalize(converter_id))

    def require(self, converter_id: str) -> DesignConverterManifest:
        converter = self.get(converter_id)
        if converter is None:
            raise ValueError("unsupported P3 design converter")
        return converter

    @staticmethod
    def _normalize_id(converter_id: str) -> str:
        return converter_id.strip()

    def _normalize(self, converter_id: str) -> str:
        normalized = self._normalize_id(converter_id)
        return self._aliases.get(normalized, normalized)


@lru_cache(maxsize=1)
def get_design_converter_plugin_registry() -> DesignConverterPluginRegistry:
    return DesignConverterPluginRegistry()


def reload_design_converter_plugin_registry() -> DesignConverterPluginRegistry:
    get_design_converter_plugin_registry.cache_clear()
    return get_design_converter_plugin_registry()
