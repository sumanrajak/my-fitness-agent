from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class ChatRequest(BaseModel):
    uid: str = Field(min_length=1, max_length=160)
    messages: list[ChatMessage] = Field(min_length=1, max_length=12)
