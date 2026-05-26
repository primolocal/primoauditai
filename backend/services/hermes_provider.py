"""
Abstract base class for Hermes AI providers.
All providers (Mock, OllamaCloud, GoogleGenAI, Remote) inherit from this.
"""
from abc import ABC, abstractmethod
from logging_config import get_logger

logger = get_logger("primoaudit.hermes.base")


class HermesProvider(ABC):
    """Abstract base for all Hermes intelligence providers."""

    @abstractmethod
    def evaluate(self, hermes_payload: dict) -> dict:
        """
        Takes a structured hermes_payload and returns structured evaluation data.
        Called by the orchestrator to generate advisory intelligence for findings.
        """
        pass

    @abstractmethod
    def evaluate_vision(self, vision_payload: dict) -> dict:
        """
        Takes a vision_payload (question, image_urls, context) and returns
        structured visual assessment.
        Returns:
            dict with supports_damage (bool), confidence (float), notes (str)
        """
        pass
