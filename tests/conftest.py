"""Shared pytest fixtures for the VoiceFlow test suite."""

from __future__ import annotations

import pytest

from voiceflow.core.config import AppConfig
from voiceflow.core.events import EventBus


@pytest.fixture
def event_bus() -> EventBus:
    """Provide a fresh EventBus instance for each test."""
    return EventBus()


@pytest.fixture
def default_config() -> AppConfig:
    """Provide a default AppConfig (no file needed)."""
    return AppConfig()
