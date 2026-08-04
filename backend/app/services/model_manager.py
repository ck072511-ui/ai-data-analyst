import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, AsyncIterator, Union
from app.core.config import settings
from app.services.cache_service import cache_service
from app.services.llm_provider import LLMProvider
from app.services.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


class LlamaCppProvider(LLMProvider):
    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        raise NotImplementedError("llama.cpp provider is not implemented yet.")

    async def stream_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        raise NotImplementedError("llama.cpp provider is not implemented yet.")
        yield ""

    async def health_check(self) -> bool:
        return False

    async def list_models(self) -> List[str]:
        return ["llama.cpp-placeholder"]


class VllmProvider(LLMProvider):
    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        raise NotImplementedError("vLLM provider is not implemented yet.")

    async def stream_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        raise NotImplementedError("vLLM provider is not implemented yet.")
        yield ""

    async def health_check(self) -> bool:
        return False

    async def list_models(self) -> List[str]:
        return ["vllm-placeholder"]


class LMStudioProvider(LLMProvider):
    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        raise NotImplementedError("LM Studio provider is not implemented yet.")

    async def stream_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        raise NotImplementedError("LM Studio provider is not implemented yet.")
        yield ""

    async def health_check(self) -> bool:
        return False

    async def list_models(self) -> List[str]:
        return ["lm-studio-placeholder"]


class HuggingFaceLocalProvider(LLMProvider):
    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        raise NotImplementedError("Hugging Face Local provider is not implemented yet.")

    async def stream_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        raise NotImplementedError("Hugging Face Local provider is not implemented yet.")
        yield ""

    async def health_check(self) -> bool:
        return False

    async def list_models(self) -> List[str]:
        return ["huggingface-local-placeholder"]

class ModelManager:
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.active_provider_name: str = settings.LLM_PROVIDER
        self.active_model_name: Optional[str] = None
        self.config_filepath = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "active_llm_config.json"
        )
        
        # Telemetry metrics
        self.total_requests = 0
        self.failed_requests = 0
        self.total_latency_sec = 0.0
        self.latency_records = 0
        self.streaming_requests = 0

        # Initialize providers
        self._initialize_providers()

    def _initialize_providers(self):
        # Initialize Ollama
        self.providers["ollama"] = OllamaProvider(
            base_url=settings.OLLAMA_URL,
            timeout=settings.OLLAMA_TIMEOUT,
            active_model=settings.LLM_DEFAULT_MODEL
        )
        # Initialize placeholders for future offline providers
        self.providers["llama.cpp"] = LlamaCppProvider()
        self.providers["vllm"] = VllmProvider()
        self.providers["lm_studio"] = LMStudioProvider()
        self.providers["huggingface_local"] = HuggingFaceLocalProvider()

    async def initialize_active_settings(self):
        """Load selected active model and provider from persistent storage (JSON/Cache)."""
        loaded_model = None
        loaded_provider = None
        
        # Try loading from local JSON config file first
        try:
            if os.path.exists(self.config_filepath):
                with open(self.config_filepath, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    loaded_model = config.get("active_model")
                    loaded_provider = config.get("active_provider")
        except Exception as e:
            logger.warning(f"Failed to read model config from file: {e}")

        # Fallback to cache if file didn't resolve it
        if not loaded_model:
            try:
                cached = await cache_service.get("active_llm_model")
                if cached:
                    loaded_model = cached.get("model")
                    loaded_provider = cached.get("provider")
            except Exception as e:
                logger.warning(f"Failed to fetch model from cache: {e}")

        # Fallbacks to settings defaults
        self.active_provider_name = loaded_provider or settings.LLM_PROVIDER
        
        if loaded_model:
            self.active_model_name = loaded_model
        else:
            if self.active_provider_name == "ollama":
                self.active_model_name = settings.LLM_DEFAULT_MODEL
            else:
                if self.active_provider_name == "llama.cpp":
                    self.active_model_name = "llama.cpp-placeholder"
                elif self.active_provider_name == "vllm":
                    self.active_model_name = "vllm-placeholder"
                elif self.active_provider_name == "lm_studio":
                    self.active_model_name = "lm-studio-placeholder"
                elif self.active_provider_name == "huggingface_local":
                    self.active_model_name = "huggingface-local-placeholder"
                else:
                    self.active_model_name = settings.LLM_DEFAULT_MODEL

        # Update model names inside the specific provider instances
        if self.active_provider_name == "ollama" and "ollama" in self.providers:
            self.providers["ollama"].active_model = self.active_model_name

    async def get_active_model(self) -> str:
        if not self.active_model_name:
            await self.initialize_active_settings()
        return self.active_model_name

    async def get_active_provider(self) -> str:
        if not self.active_provider_name:
            await self.initialize_active_settings()
        return self.active_provider_name

    def get_provider(self) -> LLMProvider:
        provider = self.providers.get(self.active_provider_name)
        if not provider:
            # Fallback to whatever provider is initialized
            provider = next(iter(self.providers.values()))
        return provider

    async def list_models(self) -> List[str]:
        """Lists available models from the active provider. Falls back cleanly if unavailable."""
        provider = self.get_provider()
        try:
            return await provider.list_models()
        except Exception as e:
            logger.error(f"Failed to list models for provider {self.active_provider_name}: {e}")
            if self.active_provider_name == "ollama":
                return ["llama3", "qwen", "mistral", "phi"]
            elif self.active_provider_name == "llama.cpp":
                return ["llama.cpp-placeholder"]
            elif self.active_provider_name == "vllm":
                return ["vllm-placeholder"]
            elif self.active_provider_name == "lm_studio":
                return ["lm-studio-placeholder"]
            elif self.active_provider_name == "huggingface_local":
                return ["huggingface-local-placeholder"]
            return ["llama3"]

    async def select_model(self, model_name: str, provider_name: Optional[str] = None) -> bool:
        """Switch models dynamically and store selection in JSON and Cache."""
        # Auto-detect provider if not explicitly given
        if not provider_name:
            if "llama.cpp" in model_name or "llama-cpp" in model_name:
                provider_name = "llama.cpp"
            elif "vllm" in model_name:
                provider_name = "vllm"
            elif "lm-studio" in model_name or "lm_studio" in model_name:
                provider_name = "lm_studio"
            elif "huggingface" in model_name or "hf-" in model_name:
                provider_name = "huggingface_local"
            else:
                provider_name = "ollama"

        if provider_name not in self.providers:
            self._initialize_providers()
            if provider_name not in self.providers:
                logger.error(f"LLM Provider {provider_name} is not initialized/configured.")
                return False

        self.active_provider_name = provider_name
        self.active_model_name = model_name

        if provider_name == "ollama":
            self.providers["ollama"].active_model = model_name

        # Persist selection in JSON file
        try:
            os.makedirs(os.path.dirname(self.config_filepath), exist_ok=True)
            with open(self.config_filepath, "w", encoding="utf-8") as f:
                json.dump({"active_model": model_name, "active_provider": provider_name}, f)
        except Exception as e:
            logger.error(f"Failed to persist model selection to file: {e}")

        # Persist selection in Cache
        try:
            await cache_service.set("active_llm_model", {"model": model_name, "provider": provider_name})
        except Exception as e:
            logger.error(f"Failed to persist model selection to cache: {e}")

        return True

    async def health_check(self) -> bool:
        provider = self.get_provider()
        try:
            return await provider.health_check()
        except Exception:
            return False

    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        self.total_requests += 1
        provider = self.get_provider()
        model = kwargs.get("model")
        if not model:
            model = await self.get_active_model()
        
        start_time = time.time()
        try:
            res = await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
                **kwargs
            )
            
            latency = time.time() - start_time
            self.total_latency_sec += latency
            self.latency_records += 1
            
            # Record metrics in monitoring service
            try:
                from app.services.monitoring_service import monitoring_service
                monitoring_service.record_ai_query(latency)
            except Exception:
                pass
                
            return res
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"LLM generate error: {e}")
            raise e

    async def stream_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        self.total_requests += 1
        self.streaming_requests += 1
        provider = self.get_provider()
        model = kwargs.get("model")
        if not model:
            model = await self.get_active_model()
        
        start_time = time.time()
        try:
            async for chunk in provider.stream_generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
                **kwargs
            ):
                yield chunk
                
            latency = time.time() - start_time
            self.total_latency_sec += latency
            self.latency_records += 1
        except Exception as e:
            self.failed_requests += 1
            logger.error(f"LLM stream_generate error: {e}")
            raise e

    def get_monitoring_stats(self) -> Dict[str, Any]:
        avg_latency = 0.0
        if self.latency_records > 0:
            avg_latency = round((self.total_latency_sec / self.latency_records) * 1000, 2)
            
        return {
            "active_model": self.active_model_name or "unknown",
            "active_provider": self.active_provider_name,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "avg_latency_ms": avg_latency,
            "streaming_statistics": {
                "streaming_requests_total": self.streaming_requests
            }
        }

model_manager = ModelManager()
