"""
Ollama LLM Integration

This module provides integration with Ollama for LLM inference.
Uses Mistral 7B model running locally via Ollama API.
"""

from llama_index.core.llms import (
    CustomLLM, 
    LLMMetadata, 
    ChatMessage, 
    MessageRole,
    CompletionResponse,
    CompletionResponseGen
)
from typing import Optional, List, AsyncIterator
import httpx
from loguru import logger
import json


class OllamaLLM(CustomLLM):
    """
    Custom LLM wrapper for Ollama API.
    
    Connects to local Ollama instance running Mistral 7B model.
    Provides synchronous and asynchronous completion methods.
    """
    
    def __init__(
        self,
        model_name: str = "mistral:7b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        context_window: int = 4096,
        num_output: int = 512,
        **kwargs
    ):
        """
        Initialize Ollama LLM.
        
        Args:
            model_name: Ollama model name (default: mistral:7b)
            base_url: Ollama API base URL
            temperature: Sampling temperature
            context_window: Maximum context window size
            num_output: Maximum tokens to generate
        """
        # Initialize parent without model_name to avoid Pydantic issues
        super().__init__(**kwargs)
        
        # Use private fields to avoid Pydantic validation
        self._model_name = model_name
        self._base_url = base_url
        self._temperature = temperature
        self._context_window = context_window
        self._num_output = num_output
        self._client = httpx.Client(timeout=300.0)  # 5 minute timeout for long responses
        
        logger.info(f"Initialized Ollama LLM: {model_name} at {self._base_url}")
    
    @property
    def metadata(self) -> LLMMetadata:
        """Return LLM metadata."""
        return LLMMetadata(
            context_window=self._context_window,
            num_output=self._num_output,
            model_name=self._model_name
        )
    
    def complete(
        self,
        prompt: str,
        formatted: bool = False,
        **kwargs
    ) -> CompletionResponse:
        """
        Complete a prompt synchronously.
        
        Args:
            prompt: Input prompt text
            formatted: Whether prompt is already formatted
            **kwargs: Additional arguments
            
        Returns:
            CompletionResponse: Completion response with generated text
        """
        try:
            response = self._client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", self._temperature),
                        "num_predict": kwargs.get("max_tokens", self._num_output)
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            
            text = result.get("response", "")
            logger.debug(f"Ollama completion: {len(text)} characters")
            
            return CompletionResponse(text=text)
        except Exception as e:
            logger.error(f"Error in Ollama completion: {e}")
            raise
    
    def stream_complete(
        self,
        prompt: str,
        formatted: bool = False,
        **kwargs
    ) -> CompletionResponseGen:
        """
        Stream completion from Ollama.
        
        Args:
            prompt: Input prompt text
            formatted: Whether prompt is already formatted
            **kwargs: Additional arguments
            
        Yields:
            CompletionResponse: Streaming completion chunks
        """
        try:
            with self._client.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": kwargs.get("temperature", self._temperature),
                        "num_predict": kwargs.get("max_tokens", self._num_output)
                    }
                }
            ) as response:
                response.raise_for_status()
                text = ""
                
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                text += chunk["response"]
                                yield CompletionResponse(text=chunk["response"], delta=chunk["response"])
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Error in Ollama streaming: {e}")
            raise
    
    def __del__(self):
        """Cleanup HTTP client."""
        if hasattr(self, '_client'):
            self._client.close()

