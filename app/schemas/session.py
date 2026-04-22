from pydantic import BaseModel

from app.models.session import SessionStatus


class LaunchRequest(BaseModel):
    profileId: str


class LaunchResponse(BaseModel):
    requestId: str
    status: str
    queuePosition: int
    etaMin: int


class SessionAccessResponse(BaseModel):
    notebookUrl: str | None
    token: str | None = None


class SessionActionResponse(BaseModel):
    sessionId: str
    status: SessionStatus
    message: str
