from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator, Union

class LLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        """
        Generate a response text for a given prompt or chat messages.
        
        Args:
            prompt: Either a simple text prompt string or a list of message dicts (e.g. ChatML format).
            system_prompt: Optional instructions for the system role.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
        """
        pass

    @abstractmethod
    async def stream_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response tokens for a given prompt or chat messages.
        
        Args:
            prompt: Either a simple text prompt string or a list of message dicts (e.g. ChatML format).
            system_prompt: Optional instructions for the system role.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider connection is healthy.
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """
        List all installed/available models from this provider.
        """
        pass
