"""First-run model download helper.

Responsibilities:
- Check if required models (Whisper, LLM, VAD) are present locally.
- Download missing models with progress reporting.
- Verify integrity of downloaded files.

This module contains the interface only.
Business logic will be implemented in Phase 4.
"""

from __future__ import annotations

from pathlib import Path


def check_models_exist(whisper_path: Path | None, llm_path: Path) -> dict[str, bool]:
    """Check whether required model files exist.

    Returns
    -------
    dict[str, bool]
        Mapping of model name to existence status.
    """
    raise NotImplementedError


async def download_model(url: str, dest: Path, *, label: str = "") -> Path:
    """Download a model file with progress reporting."""
    raise NotImplementedError
