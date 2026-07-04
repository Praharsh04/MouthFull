"""Abstract interface for LLM refinement engines.

All LLM implementations must inherit from LLMEngine and implement
the refine() method.  This enables swapping backends (e.g.,
llama-cpp ↔ Ollama) without modifying pipeline code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMEngine(ABC):
    """Base class for LLM text-refinement engines."""

    @abstractmethod
    async def load_model(self) -> None:
        """Load the LLM into memory."""

    @abstractmethod
    async def refine(self, raw_text: str) -> str:
        """Refine raw STT output into clean, corrected text.

        Parameters
        ----------
        raw_text:
            The raw transcript from the STT engine.

        Returns
        -------
        str
            The refined, corrected text.
        """

    @abstractmethod
    async def unload_model(self) -> None:
        """Release model resources."""
