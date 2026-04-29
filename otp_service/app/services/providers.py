from __future__ import annotations

from importlib import import_module

from app.models.provider_config import ProviderConfig
from app.providers.base import BaseProviderAdapter


class ProviderRegistry:
    def __init__(self):
        self._adapter_cache: dict[str, BaseProviderAdapter] = {}

    def _load_adapter_class(self, dotted_path: str):
        module_name, _, class_name = dotted_path.rpartition(".")
        if not module_name:
            raise ValueError(f"Invalid adapter path: {dotted_path}")
        module = import_module(module_name)
        return getattr(module, class_name)

    async def get_adapter(self, provider_config: ProviderConfig) -> BaseProviderAdapter:
        cached = self._adapter_cache.get(provider_config.provider_id)
        if cached is not None:
            return cached

        adapter_path = provider_config.settings_json.get(
            "adapter",
            "app.providers.adapters.LoggingEmailProvider",
        )
        adapter_cls = self._load_adapter_class(adapter_path)
        adapter = adapter_cls(
            provider_id=provider_config.provider_id,
            tier=provider_config.tier,
            settings={
                **provider_config.settings_json,
                "weight": provider_config.weight,
                "daily_limit": provider_config.daily_limit,
                "monthly_limit": provider_config.monthly_limit,
            },
        )
        self._adapter_cache[provider_config.provider_id] = adapter
        return adapter
