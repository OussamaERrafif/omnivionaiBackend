"""Fast unit tests for provider selection and request-scoped search settings."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.base_agent import BaseAgent
from app.agents.config import Config, LLMProvider


class _FailingClient:
    async def ainvoke(self, *_args, **_kwargs):
        raise RuntimeError("provider unavailable")


class _WorkingClient:
    async def ainvoke(self, *_args, **_kwargs):
        return "fallback response"


class LLMConfigurationTests(unittest.TestCase):
    def test_provider_order_uses_only_configured_keys(self):
        providers = Config.get_llm_providers(
            {
                "LLM_PROVIDER_ORDER": "groq, nvidia, openai, groq",
                "NVIDIA_API_KEY": "nvidia-test-key",
                "GROQ_API_KEY": "groq-test-key",
                "OPENAI_API_KEY": "",
            }
        )

        self.assertEqual([provider.name for provider in providers], ["groq", "nvidia"])
        self.assertEqual(providers[0].base_url, "https://api.groq.com/openai/v1")
        self.assertEqual(providers[1].base_url, "https://integrate.api.nvidia.com/v1")

    def test_search_settings_are_isolated_values(self):
        original_results = Config.MAX_RESULTS_PER_SEARCH
        deep_settings = Config.get_search_settings("deep")
        quick_settings = Config.get_search_settings("quick")

        self.assertGreater(deep_settings.max_content_length, quick_settings.max_content_length)
        self.assertEqual(Config.MAX_RESULTS_PER_SEARCH, original_results)
        self.assertIsNot(deep_settings, quick_settings)

    def test_failed_provider_retries_the_next_provider(self):
        invoke = BaseAgent._ainvoke_with_fallback(
            [
                (LLMProvider("openai", "test", "model"), _FailingClient()),
                (LLMProvider("groq", "test", "model"), _WorkingClient()),
            ]
        )

        import asyncio

        self.assertEqual(asyncio.run(invoke("test prompt")), "fallback response")


if __name__ == "__main__":
    unittest.main()
