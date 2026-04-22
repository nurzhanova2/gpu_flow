from pydantic import BaseModel

from app.models.queue import QueueStatus


class QueueCancelResponse(BaseModel):
    queueId: str
    status: QueueStatus
    message: str


class QueueAdminActionResponse(BaseModel):
    queueId: str
    status: QueueStatus
    message: str
