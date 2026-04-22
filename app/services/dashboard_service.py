from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import randint

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.integrations.metrics.base import MetricsAdapter
from app.models import Alert, LaunchProfile, Node, QueueItem, QueueStatus, Session, SessionStatus, User


class DashboardService:
    def __init__(self, db: AsyncSession, settings: Settings, metrics_adapter: MetricsAdapter) -> None:
        self.db = db
        self.settings = settings
        self.metrics_adapter = metrics_adapter

    async def get_user_dashboard(self, user_id: str) -> dict:
        user = await self.db.get(User, user_id)

        launch_profiles = await self._load_launch_profiles()

        active_sessions = await self.db.execute(
            select(Session)
            .where(Session.status.in_([SessionStatus.starting, SessionStatus.running, SessionStatus.idle]))
            .options(selectinload(Session.user), selectinload(Session.profile), selectinload(Session.node))
            .order_by(Session.created_at.desc())
        )
        all_active_sessions = list(active_sessions.scalars().all())
        user_active_sessions = [s for s in all_active_sessions if s.user_id == user_id]

        queue_result = await self.db.execute(
            select(QueueItem)
            .where(QueueItem.is_archived.is_(False), QueueItem.status.in_([QueueStatus.waiting, QueueStatus.starting, QueueStatus.running]))
            .options(selectinload(QueueItem.user), selectinload(QueueItem.profile))
            .order_by(QueueItem.priority.desc(), QueueItem.requested_at.asc())
            .limit(12)
        )
        all_queue_snapshot_items = list(queue_result.scalars().all())
        queue_snapshot_items = [item for item in all_queue_snapshot_items if item.user_id == user_id]

        my_queue = next((item for item in queue_snapshot_items if item.user_id == user_id and item.status in [QueueStatus.waiting, QueueStatus.starting, QueueStatus.running]), None)

        history_result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id, Session.status.in_([SessionStatus.completed, SessionStatus.failed, SessionStatus.terminated]))
            .options(selectinload(Session.profile))
            .order_by(Session.created_at.desc())
            .limit(8)
        )
        history = list(history_result.scalars().all())

        success_total = len(history)
        success_count = len([s for s in history if s.status == SessionStatus.completed])
        success_ratio = 100 if success_total == 0 else round((success_count / success_total) * 100)

        position_value = my_queue.queue_position if my_queue and my_queue.queue_position else 0
        eta_min = int((my_queue.eta_seconds or 0) / 60) if my_queue else 0
        queue_depth = len([q for q in queue_snapshot_items if q.status == QueueStatus.waiting])

        summary_stats = [
            {
                "id": "active",
                "label": "Активные сессии",
                "value": str(len(user_active_sessions)),
                "hint": f"{len(user_active_sessions)} сессий запущено",
                "tone": "green",
            },
            {
                "id": "position",
                "label": "Позиция в очереди",
                "value": str(position_value),
                "hint": f"ETA {eta_min} мин",
                "tone": "yellow",
            },
            {
                "id": "week",
                "label": "GPU-часы (7д)",
                "value": f"{self._calc_gpu_hours(history):.1f}",
                "hint": f"Запусков: {user.launches_7d if user else 0}",
                "tone": "blue",
            },
            {
                "id": "success",
                "label": "Успешный запуск",
                "value": f"{success_ratio}%",
                "hint": f"{success_count} успешных старта",
                "tone": "green",
            },
        ]

        my_state = None
        if my_queue:
            my_state = {
                "status": my_queue.status.value,
                "stateLabel": self._queue_state_label(my_queue.status.value),
                "queuePosition": my_queue.queue_position or 0,
                "queueTotal": queue_depth,
                "etaRange": f"{max(eta_min - 2, 1)}-{eta_min + 2} мин" if eta_min else "0-1 мин",
                "averageWaitToday": "9 мин",
                "completedAhead": max((my_queue.queue_position or 1) - 1, 0),
                "progressPercent": self._progress_percent(my_queue),
                "selectedProfile": my_queue.profile.label,
                "requestedAt": self._format_time(my_queue.requested_at),
            }

        history_items = [
            {
                "id": s.id,
                "startedAt": self._format_history_date(s.started_at or s.created_at),
                "duration": self._format_duration(s.started_at, s.ended_at),
                "profile": s.profile.label,
                "result": "completed" if s.status == SessionStatus.completed else "failed",
            }
            for s in history
        ]

        return {
            "summaryStats": summary_stats,
            "launchProfiles": launch_profiles,
            "mySessionState": my_state,
            "queueSnapshot": [
                {
                    "id": row.id,
                    "user": "Вы" if row.user_id == user_id else row.user.full_name,
                    "profile": row.profile.label,
                    "status": row.status.value,
                    "waitMin": int((row.eta_seconds or 0) / 60),
                    "mine": row.user_id == user_id,
                }
                for row in queue_snapshot_items
            ],
            "activeSessions": [
                {
                    "id": session.id,
                    "user": "Вы",
                    "node": session.node.hostname if session.node else "n/a",
                    "gpu": session.node.gpu_model if session.node else "CPU",
                    "profile": session.profile.label,
                    "status": session.status.value,
                    "durationMin": self._duration_minutes(session.started_at),
                    "gpuUsage": int(session.gpu_usage),
                    "memoryUsage": int(session.memory_usage),
                    "cpuUsage": int(session.cpu_usage),
                    "mine": session.user_id == user_id,
                    "notebookUrl": session.notebook_url,
                }
                for session in user_active_sessions
            ],
            "recentSessionHistory": history_items,
            "history": history_items,
            "charts": self._build_user_charts(queue_depth),
        }

    async def get_admin_dashboard(self) -> dict:
        now = datetime.now(UTC)

        queue_rows_result = await self.db.execute(
            select(QueueItem)
            .where(QueueItem.is_archived.is_(False), QueueItem.status.in_([QueueStatus.waiting, QueueStatus.starting, QueueStatus.running]))
            .options(selectinload(QueueItem.user), selectinload(QueueItem.profile))
            .order_by(QueueItem.priority.desc(), QueueItem.requested_at.asc())
            .limit(50)
        )
        queue_rows = list(queue_rows_result.scalars().all())

        sessions_result = await self.db.execute(
            select(Session)
            .where(Session.status.in_([SessionStatus.starting, SessionStatus.running, SessionStatus.idle, SessionStatus.terminating]))
            .options(selectinload(Session.user), selectinload(Session.profile), selectinload(Session.node))
            .order_by(Session.created_at.desc())
            .limit(50)
        )
        sessions = list(sessions_result.scalars().all())

        node_result = await self.db.execute(select(Node).order_by(Node.hostname.asc()))
        nodes = list(node_result.scalars().all())

        users_result = await self.db.execute(select(User).order_by(User.full_name.asc()))
        users = list(users_result.scalars().all())

        alerts_result = await self.db.execute(select(Alert).where(Alert.resolved.is_(False)).order_by(Alert.created_at.desc()).limit(5))
        alerts = list(alerts_result.scalars().all())

        total_gpu = sum(node.gpu_total for node in nodes)
        used_gpu = sum(node.gpu_used for node in nodes)
        usage = await self.metrics_adapter.get_usage(total_gpu, used_gpu, len([q for q in queue_rows if q.status == QueueStatus.waiting]))

        active_count = len([s for s in sessions if s.status in [SessionStatus.running, SessionStatus.idle, SessionStatus.starting]])
        avg_wait = 0
        waiting_items = [q for q in queue_rows if q.status == QueueStatus.waiting]
        if waiting_items:
            avg_wait = round(sum((q.eta_seconds or 0) / 60 for q in waiting_items) / len(waiting_items))

        node_overview = [
            {
                "id": node.id,
                "hostname": node.hostname,
                "region": node.region,
                "gpuModel": node.gpu_model,
                "gpuTotal": node.gpu_total,
                "gpuUsed": node.gpu_used,
                "status": node.status.value,
                "activeUser": self._find_active_user(node.id, sessions),
                "cpu": node.cpu_usage,
                "ram": node.ram_usage,
                "temperature": node.temperature,
                "uptimeHours": node.uptime_hours,
            }
            for node in nodes
        ]
        queue_rows_payload = [
            {
                "id": q.id,
                "user": q.user.full_name,
                "team": q.user.team,
                "requestedAt": self._format_time(q.requested_at),
                "status": q.status.value,
                "profile": q.profile.label,
                "nodeTarget": q.node_target or "pending",
                "waitMin": int((q.eta_seconds or 0) / 60),
                "reason": q.failure_reason or self._queue_reason(q.status.value),
            }
            for q in queue_rows
        ]
        sessions_payload = [
            {
                "id": s.id,
                "user": s.user.full_name,
                "team": s.user.team,
                "node": s.node.hostname if s.node else "n/a",
                "profile": s.profile.label,
                "gpu": s.node.gpu_model if s.node else "CPU",
                "startedAt": self._format_time(s.started_at or s.created_at),
                "durationMin": self._duration_minutes(s.started_at),
                "status": s.status.value,
                "gpuUsage": int(s.gpu_usage),
                "memUsage": int(s.memory_usage),
                "cpuUsage": int(s.cpu_usage),
            }
            for s in sessions
        ]
        alerts_payload = [
            {"id": a.id, "level": a.level.value, "message": a.message, "createdAt": self._relative_time(a.created_at, now)}
            for a in alerts
        ]
        chart_payload = {
            "clusterUsageSeries": self._build_cluster_usage_series(usage["queueDepth"]),
            "nodeLoadSeries": self._build_node_load_series(nodes),
        }

        return {
            "adminKpis": [
                {"id": "nodes", "label": "GPU-узлы в сети", "value": f"{len(nodes)} / {len(nodes)}", "hint": "доступность 100%", "tone": "green"},
                {"id": "active", "label": "Активные сессии", "value": str(active_count), "hint": "включая idle", "tone": "blue"},
                {
                    "id": "queue",
                    "label": "Пользователи в очереди",
                    "value": str(len(waiting_items)),
                    "hint": f"+{randint(0, 3)} за последний час",
                    "tone": "yellow",
                },
                {"id": "wait", "label": "Среднее ожидание", "value": f"{avg_wait}м", "hint": "по waiting-заявкам", "tone": "yellow"},
                {"id": "util", "label": "Утилизация GPU-кластера", "value": f"{usage['gpuUtilization']}%", "hint": "текущая нагрузка", "tone": "green"},
            ],
            "adminAlerts": alerts_payload,
            "nodeOverview": node_overview,
            "queueRows": queue_rows_payload,
            "activeSessionsAdmin": sessions_payload,
            "clusterUsageSeries": chart_payload["clusterUsageSeries"],
            "nodeLoadSeries": chart_payload["nodeLoadSeries"],
            "userActivityRows": self._build_user_activity_rows(users, sessions, queue_rows),
            "alerts": alerts_payload,
            "nodes": node_overview,
            "queue": queue_rows_payload,
            "sessions": sessions_payload,
            "charts": chart_payload,
        }

    async def _load_launch_profiles(self) -> list[dict]:
        result = await self.db.execute(select(LaunchProfile).order_by(LaunchProfile.recommended.desc(), LaunchProfile.id.asc()))
        profiles = list(result.scalars().all())
        return [
            {
                "id": p.id,
                "label": p.label,
                "description": p.description,
                "queue": p.queue_hint,
                "tag": p.tag,
                "icon": p.icon,
                "recommended": p.recommended,
            }
            for p in profiles
        ]

    def _calc_gpu_hours(self, sessions: list[Session]) -> float:
        total_minutes = 0
        for session in sessions:
            if session.started_at and session.ended_at:
                total_minutes += int((session.ended_at - session.started_at).total_seconds() / 60)
        return round(total_minutes / 60, 1)

    def _duration_minutes(self, started_at: datetime | None) -> int:
        if not started_at:
            return 0
        return int((datetime.now(UTC) - started_at).total_seconds() / 60)

    def _queue_state_label(self, status: str) -> str:
        labels = {
            "waiting": "Заявка в очереди, ожидается выделение GPU",
            "starting": "Запуск сессии в процессе",
            "running": "Сессия запущена и активна",
            "failed": "Запуск завершился ошибкой",
            "cancelled": "Заявка отменена",
        }
        return labels.get(status, "Неизвестный статус")

    def _progress_percent(self, queue_item: QueueItem) -> int:
        if queue_item.status == QueueStatus.waiting:
            position = queue_item.queue_position or 1
            return max(8, min(95, 100 - (position * 12)))
        if queue_item.status == QueueStatus.starting:
            return 88
        if queue_item.status == QueueStatus.running:
            return 100
        return 0

    def _format_time(self, dt: datetime) -> str:
        return dt.strftime("%H:%M")

    def _format_history_date(self, dt: datetime) -> str:
        return dt.strftime("%d %b, %H:%M")

    def _format_duration(self, started_at: datetime | None, ended_at: datetime | None) -> str:
        if not started_at or not ended_at:
            return "0м"
        minutes = int((ended_at - started_at).total_seconds() / 60)
        hours = minutes // 60
        rest = minutes % 60
        if hours:
            return f"{hours}ч {rest}м"
        return f"{rest}м"

    def _build_user_charts(self, queue_depth: int) -> dict:
        base_time = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
        gpu_series = []
        queue_series = []
        for index in range(24):
            point_time = (base_time + timedelta(hours=index)).strftime("%H:%M")
            gpu_series.append(
                {
                    "time": point_time,
                    "nodeAlpha": max(5, min(99, 42 + ((index * 7) % 51))),
                    "nodeBeta": max(5, min(99, 38 + ((index * 5) % 57))),
                    "nodeGamma": max(3, min(95, 27 + ((index * 9) % 49))),
                }
            )
            queue_series.append(
                {
                    "time": point_time,
                    "queued": max(1, queue_depth + ((index % 5) - 2)),
                    "avgWait": max(2, 7 + (index % 6)),
                }
            )

        usage_split = [
            {"id": "busy", "label": "GPU занято", "value": 68, "color": "var(--tone-green)"},
            {"id": "idle", "label": "GPU простаивает", "value": 24, "color": "var(--tone-yellow)"},
            {"id": "maintenance", "label": "Техобслуживание", "value": 8, "color": "var(--tone-blue)"},
        ]

        return {
            "gpuUtilizationSeries": gpu_series,
            "queueTrendSeries": queue_series,
            "usageSplit": usage_split,
        }

    def _relative_time(self, created_at: datetime, now: datetime) -> str:
        minutes = int((now - created_at).total_seconds() / 60)
        if minutes < 1:
            return "только что"
        if minutes < 60:
            return f"{minutes} мин назад"
        hours = minutes // 60
        return f"{hours} ч назад"

    def _find_active_user(self, node_id: str, sessions: list[Session]) -> str | None:
        for session in sessions:
            if session.node_id == node_id and session.status in [SessionStatus.running, SessionStatus.idle, SessionStatus.starting]:
                return session.user.full_name
        return None

    def _queue_reason(self, status: str) -> str:
        reasons = {
            "waiting": "Ожидание свободного ресурса",
            "starting": "Подготовка среды запуска",
            "running": "Сессия активна",
            "failed": "Ошибка запуска",
            "cancelled": "Заявка отменена",
        }
        return reasons.get(status, "")

    def _build_cluster_usage_series(self, queue_depth: int) -> list[dict]:
        start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
        points = []
        for i in range(24):
            t = (start + timedelta(hours=i)).strftime("%H:%M")
            points.append(
                {
                    "time": t,
                    "gpuCluster": max(14, min(98, 48 + ((i * 6) % 45))),
                    "queueDepth": max(1, queue_depth + ((i % 5) - 1)),
                    "activeSessions": max(1, 3 + (i % 4)),
                }
            )
        return points

    def _build_node_load_series(self, nodes: list) -> list[dict]:
        start = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
        points = []
        for i in range(24):
            row = {"time": (start + timedelta(hours=i)).strftime("%H:%M")}
            for idx, node in enumerate(nodes):
                key = node.hostname.split("-")[1] if "-" in node.hostname else f"node{idx + 1}"
                row[key] = max(0, min(99, node.cpu_usage + randint(-15, 15)))
            points.append(row)
        return points

    def _build_user_activity_rows(self, users: list[User], sessions: list[Session], queue_rows: list[QueueItem]) -> list[dict]:
        rows: list[dict] = []
        for user in users:
            user_active = len([s for s in sessions if s.user_id == user.id and s.status in [SessionStatus.running, SessionStatus.idle, SessionStatus.starting]])
            user_queued = len([q for q in queue_rows if q.user_id == user.id and q.status == QueueStatus.waiting])

            if user.is_blocked:
                activity_status = "blocked"
            elif user_active > 0:
                activity_status = "active"
            elif user_queued > 0:
                activity_status = "queued"
            else:
                activity_status = "idle"

            rows.append(
                {
                    "id": user.id,
                    "user": user.full_name,
                    "team": user.team,
                    "launches7d": user.launches_7d,
                    "active": user_active,
                    "queued": user_queued,
                    "maxActiveSessions": user.max_active_sessions,
                    "maxQueuedRequests": user.max_queued_requests,
                    "avgRuntime": f"{user.avg_runtime_minutes}m",
                    "status": activity_status,
                }
            )

        rows.sort(key=lambda x: x["user"])
        return rows
