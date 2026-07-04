"""Shared pytest fixtures for the MouthFull test suite."""

from __future__ import annotations

import pytest

from mouthfull.configs.config import AppConfig
from mouthfull.utils.events import EventBus


@pytest.fixture
def event_bus() -> EventBus:
    """Provide a fresh EventBus instance for each test."""
    return EventBus()


@pytest.fixture
def default_config() -> AppConfig:
    """Provide a default AppConfig (no file needed)."""
    return AppConfig()
