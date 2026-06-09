from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl


class UploadFileResponse(BaseModel):
    session_id: UUID
    status: str


class YoutubeUploadRequest(BaseModel):
    url: str


class YoutubeUploadResponse(BaseModel):
    session_id: UUID
    status: str


class DamageEventData(BaseModel):
    timestamp_ms: int
    damage_value: int
    progress: int


class DoneEventData(BaseModel):
    total_damage: int
    max_damage: int
    avg_damage: float
    hit_count: int


class ErrorEventData(BaseModel):
    message: str


class SummaryResponse(BaseModel):
    session_id: UUID
    total_damage: int
    max_damage: int
    avg_damage: float
    hit_count: int
    status: str


class DamageLogItem(BaseModel):
    timestamp_ms: int
    damage_value: int


class DamageLogsResponse(BaseModel):
    logs: list[DamageLogItem]
    total: int


class HistorySessionItem(BaseModel):
    id: UUID
    video_name: Optional[str]
    total_damage: Optional[int]
    status: Literal['pending', 'processing', 'done', 'error']
    created_at: datetime


class HistoryResponse(BaseModel):
    sessions: list[HistorySessionItem]
    total: int
