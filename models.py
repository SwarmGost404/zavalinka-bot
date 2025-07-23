from pydantic import BaseModel
from typing import Optional

class SongText(BaseModel):
    title: str
    text: str
    region: str
    category: Optional[str] = None

class SongAudio(BaseModel):
    title: str
    audio: bin
    region: str
    category: Optional[str] = None