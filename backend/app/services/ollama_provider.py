import json
import logging
import asyncio
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator, Union
from app.services.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 30, active_model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.active_model = active_model
        # Configure client with standard timeouts
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(float(timeout), connect=5.0))

    async def _request_with_retry(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{path}"
        max_retries = 3
        delay = 1.0
        backoff = 2.0
        
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                response = await self.client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as e:
                last_exception = e
                if attempt == max_retries:
                    logger.error(f"Ollama request to {url} failed after {max_retries} attempts: {e}")
                    raise e
                logger.warning(f"Ollama attempt {attempt} failed for {url}, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
                delay *= backoff
        raise last_exception or httpx.HTTPError("Unknown Ollama connection error")

    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        # Format messages for the Chat API
        if isinstance(prompt, str):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        model = kwargs.get("model", self.active_model)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            response = await self._request_with_retry("POST", "/api/chat", json=payload)
            res_json = response.json()
            return res_json.get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error(f"Ollama generate failed: {e}")
            raise e

    async def stream_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        if isinstance(prompt, str):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        else:
            messages = prompt

        model = kwargs.get("model", self.active_model)
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        url = f"{self.base_url}/api/chat"
        
        async def connect_stream():
            return await self.client.send(
                self.client.build_request("POST", url, json=payload),
                stream=True
            )

        response = None
        max_retries = 3
        delay = 1.0
        backoff = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                response = await connect_stream()
                response.raise_for_status()
                break
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Ollama stream connection failed after {max_retries} attempts: {e}")
                    raise e
                logger.warning(f"Ollama stream attempt {attempt} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
                delay *= backoff

        try:
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue
        finally:
            if response:
                await response.aclose()

    async def health_check(self) -> bool:
        try:
            # Send a quick check to /api/tags which is fast
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        try:
            response = await self._request_with_retry("GET", "/api/tags", timeout=5.0)
            data = response.json()
            models = data.get("models", [])
            return [m.get("name") for m in models if m.get("name")]
        except Exception as e:
            logger.warning(f"Failed to query Ollama models: {e}")
            # Do not throw, return empty list to report cleanly
            return []
