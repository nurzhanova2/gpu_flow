from typing import Any

from pydantic import BaseModel


class UserDashboardResponse(BaseModel):
    summaryStats: list[dict[str, Any]]
    launchProfiles: list[dict[str, Any]]
    mySessionState: dict[str, Any] | None
    queueSnapshot: list[dict[str, Any]]
    activeSessions: list[dict[str, Any]]
    recentSessionHistory: list[dict[str, Any]]
    history: list[dict[str, Any]] = []
    charts: dict[str, Any]


class AdminDashboardResponse(BaseModel):
    adminKpis: list[dict[str, Any]]
    adminAlerts: list[dict[str, Any]]
    nodeOverview: list[dict[str, Any]]
    queueRows: list[dict[str, Any]]
    activeSessionsAdmin: list[dict[str, Any]]
    clusterUsageSeries: list[dict[str, Any]]
    nodeLoadSeries: list[dict[str, Any]]
    userActivityRows: list[dict[str, Any]]
    alerts: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []
    charts: dict[str, Any] = {}
