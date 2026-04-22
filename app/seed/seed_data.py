from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.security import hash_password
from app.models import (
    Alert,
    AlertLevel,
    LaunchProfile,
    Node,
    NodeStatus,
    QueueItem,
    QueueStatus,
    Session,
    SessionStatus,
    User,
    UserRole,
)


async def seed_data(db: AsyncSession, settings: Settings) -> None:
    seed_user_specs = [
        {
            "username": "admin",
            "full_name": "Admin GPUFlow",
            "email": "admin@gpuflow.local",
            "team": "Platform",
            "password": "admin123",
            "role": UserRole.admin,
            "max_active_sessions": 3,
            "max_queued_requests": 5,
            "launches_7d": 25,
            "avg_runtime_minutes": 61,
        },
        {
            "username": "demo",
            "full_name": "Вы",
            "email": "demo@gpuflow.local",
            "team": "NLP",
            "password": "user12345",
            "role": UserRole.user,
            "max_active_sessions": settings.default_max_active_sessions,
            "max_queued_requests": settings.default_max_queued_requests,
            "launches_7d": 14,
            "avg_runtime_minutes": 52,
        },
        {
            "username": "mina",
            "full_name": "Mina K.",
            "email": "mina@gpuflow.local",
            "team": "Vision",
            "password": "user12345",
            "role": UserRole.user,
            "max_active_sessions": settings.default_max_active_sessions,
            "max_queued_requests": settings.default_max_queued_requests,
            "launches_7d": 17,
            "avg_runtime_minutes": 63,
        },
        {
            "username": "alex",
            "full_name": "Alex J.",
            "email": "alex@gpuflow.local",
            "team": "Analytics",
            "password": "user12345",
            "role": UserRole.user,
            "max_active_sessions": settings.default_max_active_sessions,
            "max_queued_requests": settings.default_max_queued_requests,
            "launches_7d": 11,
            "avg_runtime_minutes": 38,
        },
        {
            "username": "tim",
            "full_name": "Tim R.",
            "email": "tim@gpuflow.local",
            "team": "Vision",
            "password": "user12345",
            "role": UserRole.user,
            "max_active_sessions": settings.default_max_active_sessions,
            "max_queued_requests": settings.default_max_queued_requests,
            "launches_7d": 12,
            "avg_runtime_minutes": 46,
        },
        {
            "username": "nora",
            "full_name": "Nora P.",
            "email": "nora@gpuflow.local",
            "team": "Analytics",
            "password": "user12345",
            "role": UserRole.user,
            "max_active_sessions": settings.default_max_active_sessions,
            "max_queued_requests": settings.default_max_queued_requests,
            "launches_7d": 8,
            "avg_runtime_minutes": 29,
        },
    ]

    existing = await db.execute(select(User.id).limit(1))
    if existing.first() is not None:
        if not settings.seed_sync_existing_users:
            return

        existing_seed_users_result = await db.execute(
            select(User).where(User.username.in_([spec["username"] for spec in seed_user_specs]))
        )
        existing_seed_users = {user.username: user for user in existing_seed_users_result.scalars().all()}

        for spec in seed_user_specs:
            user = existing_seed_users.get(spec["username"])
            if user:
                user.full_name = spec["full_name"]
                user.email = spec["email"]
                user.team = spec["team"]
                user.password_hash = hash_password(spec["password"])
                user.role = spec["role"]
                user.max_active_sessions = spec["max_active_sessions"]
                user.max_queued_requests = spec["max_queued_requests"]
                user.launches_7d = spec["launches_7d"]
                user.avg_runtime_minutes = spec["avg_runtime_minutes"]
                user.is_blocked = False
                user.failed_login_attempts = 0
                user.login_locked_until = None
            else:
                db.add(
                    User(
                        username=spec["username"],
                        full_name=spec["full_name"],
                        email=spec["email"],
                        team=spec["team"],
                        password_hash=hash_password(spec["password"]),
                        role=spec["role"],
                        max_active_sessions=spec["max_active_sessions"],
                        max_queued_requests=spec["max_queued_requests"],
                        launches_7d=spec["launches_7d"],
                        avg_runtime_minutes=spec["avg_runtime_minutes"],
                        is_blocked=False,
                        failed_login_attempts=0,
                        login_locked_until=None,
                    )
                )

        await db.commit()
        return

    profiles = [
        LaunchProfile(
            id="cpu-standard",
            label="CPU Standard",
            description="Без GPU. Мгновенный запуск.",
            queue_hint="Без очереди",
            tag="Быстро",
            icon="CPU",
            recommended=False,
            gpu_count=0,
            cpu_cores=4,
            memory_gb=8,
        ),
        LaunchProfile(
            id="gpu-basic",
            label="GPU Basic",
            description="1x NVIDIA T4, сбалансированная нагрузка.",
            queue_hint="~6 мин",
            tag="Баланс",
            icon="T4",
            recommended=False,
            gpu_count=1,
            cpu_cores=6,
            memory_gb=16,
        ),
        LaunchProfile(
            id="gpu-pro",
            label="GPU Pro",
            description="1x NVIDIA A100 с увеличенной памятью.",
            queue_hint="~12 мин",
            tag="Рекомендуем",
            icon="A100",
            recommended=True,
            gpu_count=1,
            cpu_cores=8,
            memory_gb=32,
        ),
        LaunchProfile(
            id="gpu-max",
            label="GPU Max",
            description="2x A100 для длительных задач обучения.",
            queue_hint="~25 мин",
            tag="Максимум",
            icon="2xA100",
            recommended=False,
            gpu_count=2,
            cpu_cores=16,
            memory_gb=64,
        ),
    ]

    users = [
        User(
            username="admin",
            full_name="Admin GPUFlow",
            email="admin@gpuflow.local",
            team="Platform",
            password_hash=hash_password("admin123"),
            role=UserRole.admin,
            max_active_sessions=3,
            max_queued_requests=5,
            launches_7d=25,
            avg_runtime_minutes=61,
        ),
        User(
            username="demo",
            full_name="Вы",
            email="demo@gpuflow.local",
            team="NLP",
            password_hash=hash_password("user12345"),
            role=UserRole.user,
            launches_7d=14,
            avg_runtime_minutes=52,
        ),
        User(
            username="mina",
            full_name="Mina K.",
            email="mina@gpuflow.local",
            team="Vision",
            password_hash=hash_password("user12345"),
            role=UserRole.user,
            launches_7d=17,
            avg_runtime_minutes=63,
        ),
        User(
            username="alex",
            full_name="Alex J.",
            email="alex@gpuflow.local",
            team="Analytics",
            password_hash=hash_password("user12345"),
            role=UserRole.user,
            launches_7d=11,
            avg_runtime_minutes=38,
        ),
        User(
            username="tim",
            full_name="Tim R.",
            email="tim@gpuflow.local",
            team="Vision",
            password_hash=hash_password("user12345"),
            role=UserRole.user,
            launches_7d=12,
            avg_runtime_minutes=46,
        ),
        User(
            username="nora",
            full_name="Nora P.",
            email="nora@gpuflow.local",
            team="Analytics",
            password_hash=hash_password("user12345"),
            role=UserRole.user,
            launches_7d=8,
            avg_runtime_minutes=29,
        ),
    ]

    nodes = [
        Node(
            hostname="node-alpha-01",
            region="rack-a",
            gpu_model="A100-80GB",
            gpu_total=1,
            gpu_used=1,
            status=NodeStatus.healthy,
            cpu_usage=68,
            ram_usage=74,
            temperature=69,
            uptime_hours=214,
        ),
        Node(
            hostname="node-beta-02",
            region="rack-a",
            gpu_model="A100-40GB",
            gpu_total=1,
            gpu_used=1,
            status=NodeStatus.healthy,
            cpu_usage=54,
            ram_usage=61,
            temperature=63,
            uptime_hours=188,
        ),
        Node(
            hostname="node-gamma-03",
            region="rack-b",
            gpu_model="T4",
            gpu_total=1,
            gpu_used=1,
            status=NodeStatus.healthy,
            cpu_usage=34,
            ram_usage=43,
            temperature=57,
            uptime_hours=166,
        ),
    ]

    db.add_all(profiles)
    db.add_all(users)
    db.add_all(nodes)
    await db.flush()

    by_username = {u.username: u for u in users}
    by_profile = {p.id: p for p in profiles}
    by_node = {n.hostname: n for n in nodes}

    now = datetime.now(UTC)

    session_demo = Session(
        user_id=by_username["demo"].id,
        profile_id=by_profile["gpu-pro"].id,
        node_id=by_node["node-beta-02"].id,
        status=SessionStatus.running,
        started_at=now - timedelta(minutes=47),
        status_updated_at=now - timedelta(minutes=1),
        last_activity_at=now,
        slurm_job_id="slurm_seed_1",
        jupyter_server_id="jhub_seed_1",
        notebook_url="https://mock-jupyter.local/user/demo/lab?session=seed1",
        gpu_usage=83,
        memory_usage=69,
        cpu_usage=42,
    )

    session_mina = Session(
        user_id=by_username["mina"].id,
        profile_id=by_profile["gpu-max"].id,
        node_id=by_node["node-alpha-01"].id,
        status=SessionStatus.running,
        started_at=now - timedelta(minutes=102),
        status_updated_at=now - timedelta(minutes=2),
        last_activity_at=now,
        slurm_job_id="slurm_seed_2",
        jupyter_server_id="jhub_seed_2",
        notebook_url="https://mock-jupyter.local/user/mina/lab?session=seed2",
        gpu_usage=91,
        memory_usage=82,
        cpu_usage=67,
    )

    session_alex = Session(
        user_id=by_username["alex"].id,
        profile_id=by_profile["gpu-basic"].id,
        node_id=by_node["node-gamma-03"].id,
        status=SessionStatus.idle,
        started_at=now - timedelta(minutes=31),
        status_updated_at=now - timedelta(minutes=5),
        last_activity_at=now - timedelta(minutes=6),
        idle_since=now - timedelta(minutes=6),
        slurm_job_id="slurm_seed_3",
        jupyter_server_id="jhub_seed_3",
        notebook_url="https://mock-jupyter.local/user/alex/lab?session=seed3",
        gpu_usage=18,
        memory_usage=35,
        cpu_usage=22,
    )

    history_session = Session(
        user_id=by_username["demo"].id,
        profile_id=by_profile["gpu-basic"].id,
        node_id=by_node["node-gamma-03"].id,
        status=SessionStatus.completed,
        started_at=now - timedelta(hours=4, minutes=20),
        ended_at=now - timedelta(hours=3, minutes=38),
        status_updated_at=now - timedelta(hours=3, minutes=38),
        slurm_job_id="slurm_seed_hist_1",
        jupyter_server_id="jhub_seed_hist_1",
        notebook_url="https://mock-jupyter.local/user/demo/lab?session=seed4",
        gpu_usage=0,
        memory_usage=0,
        cpu_usage=0,
    )

    failed_history = Session(
        user_id=by_username["demo"].id,
        profile_id=by_profile["gpu-max"].id,
        status=SessionStatus.failed,
        created_at=now - timedelta(days=1, hours=3),
        started_at=now - timedelta(days=1, hours=3),
        ended_at=now - timedelta(days=1, hours=2, minutes=45),
        status_updated_at=now - timedelta(days=1, hours=2, minutes=45),
        termination_reason="seed_failure",
        slurm_job_id="slurm_seed_hist_2",
    )

    db.add_all([session_demo, session_mina, session_alex, history_session, failed_history])
    await db.flush()

    queue_items = [
        QueueItem(
            user_id=by_username["demo"].id,
            profile_id=by_profile["gpu-pro"].id,
            status=QueueStatus.running,
            requested_at=now - timedelta(minutes=55),
            status_updated_at=now - timedelta(minutes=47),
            queue_position=0,
            eta_seconds=0,
            node_target="node-beta-02",
            slurm_job_id=session_demo.slurm_job_id,
            is_archived=False,
        ),
        QueueItem(
            user_id=by_username["mina"].id,
            profile_id=by_profile["gpu-max"].id,
            status=QueueStatus.running,
            requested_at=now - timedelta(minutes=120),
            status_updated_at=now - timedelta(minutes=102),
            queue_position=0,
            eta_seconds=0,
            node_target="node-alpha-01",
            slurm_job_id=session_mina.slurm_job_id,
            is_archived=False,
        ),
        QueueItem(
            user_id=by_username["alex"].id,
            profile_id=by_profile["gpu-basic"].id,
            status=QueueStatus.running,
            requested_at=now - timedelta(minutes=39),
            status_updated_at=now - timedelta(minutes=31),
            queue_position=0,
            eta_seconds=0,
            node_target="node-gamma-03",
            slurm_job_id=session_alex.slurm_job_id,
            is_archived=False,
        ),
        QueueItem(
            user_id=by_username["tim"].id,
            profile_id=by_profile["gpu-pro"].id,
            status=QueueStatus.waiting,
            requested_at=now - timedelta(minutes=14),
            status_updated_at=now - timedelta(minutes=14),
            queue_position=1,
            eta_seconds=8 * 60,
        ),
        QueueItem(
            user_id=by_username["nora"].id,
            profile_id=by_profile["cpu-standard"].id,
            status=QueueStatus.waiting,
            requested_at=now - timedelta(minutes=8),
            status_updated_at=now - timedelta(minutes=8),
            queue_position=2,
            eta_seconds=13 * 60,
        ),
        QueueItem(
            user_id=by_username["demo"].id,
            profile_id=by_profile["gpu-pro"].id,
            status=QueueStatus.waiting,
            requested_at=now - timedelta(minutes=5),
            status_updated_at=now - timedelta(minutes=5),
            queue_position=3,
            eta_seconds=18 * 60,
        ),
    ]

    db.add_all(queue_items)
    await db.flush()

    session_demo.queue_item_id = queue_items[0].id
    session_mina.queue_item_id = queue_items[1].id
    session_alex.queue_item_id = queue_items[2].id

    alerts = [
        Alert(level=AlertLevel.critical, message="Глубина очереди GPU превысила 8 пользователей", created_at=now - timedelta(minutes=2)),
        Alert(level=AlertLevel.warning, message="node-gamma-03 в idle более 14 минут", created_at=now - timedelta(minutes=6)),
        Alert(level=AlertLevel.info, message="node-alpha-01 работает в штатном режиме", created_at=now - timedelta(minutes=11)),
    ]

    db.add_all(alerts)
    await db.commit()
