from uuid import uuid4
from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: str = Field("processing")
    answer: str = Field("processing")
    text: str
