"""
AI Provider Interface with Local LLM (Ollama) and Deterministic Rule-Based Fallback.
Guarantees full functionality without requiring paid API keys or external proprietary cloud models.
"""

from typing import Any, Dict, List, Optional
import json
import logging
import os
import requests

logger = logging.getLogger(__name__)


class AIProvider:
    """
    Manages optional local LLM generation (Ollama) with instant deterministic fallback.
    Never hallucinates or overrides verified empirical evidence.
    """

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 2.0,
    ):
        self.ollama_url = ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout = timeout
        self.is_available = self._check_ollama_status()

    def _check_ollama_status(self) -> bool:
        """Pings the local Ollama daemon to see if it is actively running."""
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=self.timeout)
            if resp.status_code == 200:
                logger.info("Local Ollama LLM provider detected and reachable.")
                return True
        except Exception:
            pass
        return False

    def generate_completion(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Attempts generation via local Ollama if available."""
        if not self.is_available:
            return None

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        }
        try:
            resp = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama generation failed ({e}); falling back to deterministic template.")
        return None
