from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        self._subscribers[event_type].append(callback)

        def unsubscribe() -> None:
            self._subscribers[event_type].remove(callback)

        return unsubscribe

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        for callback in tuple(self._subscribers.get(event_type, ())):
            callback(payload)
