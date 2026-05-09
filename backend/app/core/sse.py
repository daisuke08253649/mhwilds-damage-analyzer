import asyncio
from typing import Optional, TypedDict


class SSEItem(TypedDict):
    event: str
    data: dict[str, int | float | str]


class SSEQueueManager:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Optional[SSEItem]]] = {}

    def get_or_create(self, session_id: str) -> asyncio.Queue[Optional[SSEItem]]:
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
        return self._queues[session_id]

    def get(self, session_id: str) -> Optional[asyncio.Queue[Optional[SSEItem]]]:
        return self._queues.get(session_id)

    def remove(self, session_id: str) -> None:
        self._queues.pop(session_id, None)


sse_manager = SSEQueueManager()
