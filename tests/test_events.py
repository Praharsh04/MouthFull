import pytest
from mouthfull.utils.events import EventBus, StatusChanged, Event
import asyncio

class DummyEvent(Event):
    value: int

@pytest.mark.asyncio
async def test_event_bus():
    bus = EventBus()
    received = []

    async def handler(event: DummyEvent):
        received.append(event.value)

    bus.subscribe(DummyEvent, handler)
    await bus.emit(DummyEvent(value=42))

    assert len(received) == 1
    assert received[0] == 42

    bus.unsubscribe(DummyEvent, handler)
    await bus.emit(DummyEvent(value=100))

    # Should not receive the second event
    assert len(received) == 1
