import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SectionHeader from "../components/ui/SectionHeader";
import Badge from "../components/ui/Badge";
import UserSummaryStats from "../components/dashboard/UserSummaryStats";
import SessionLaunchPanel from "../components/sessions/SessionLaunchPanel";
import MyQueueCard from "../components/queue/MyQueueCard";
import ActiveSessionsGrid from "../components/sessions/ActiveSessionsGrid";
import UserChartsPanel from "../components/charts/UserChartsPanel";
import SessionHistoryTable from "../components/sessions/SessionHistoryTable";
import {
  cancelQueueItem,
  getSessionAccess,
  getUserDashboard,
  launchSession,
  relaunchSession,
} from "../api/dashboardApi";
import { useAuth } from "../context/AuthContext";
import { useRealtime } from "../context/RealtimeContext";
import { getSafeNotebookUrl } from "../lib/urlSafety";

export default function UserDashboard() {
  const { accessToken } = useAuth();
  const { subscribe, connected } = useRealtime();
  const reloadTimerRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [launchPending, setLaunchPending] = useState(false);
  const [cancelPending, setCancelPending] = useState(false);
  const [openPending, setOpenPending] = useState(false);
  const [relaunchingId, setRelaunchingId] = useState(null);

  const loadDashboard = useCallback(async ({ silent = false } = {}) => {
    if (!accessToken) return;

    if (!silent) {
      setLoading(true);
    }

    try {
      const payload = await getUserDashboard(accessToken);
      setDashboard(payload);
      setError("");
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [accessToken]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const unsubscribe = subscribe((event) => {
      if (!["queue.updated", "session.updated", "node.updated"].includes(event?.event)) return;

      if (reloadTimerRef.current) {
        clearTimeout(reloadTimerRef.current);
      }

      reloadTimerRef.current = setTimeout(() => {
        loadDashboard({ silent: true });
      }, 350);
    });

    return () => {
      unsubscribe();
      if (reloadTimerRef.current) {
        clearTimeout(reloadTimerRef.current);
      }
    };
  }, [loadDashboard, subscribe]);

  const summaryStats = dashboard?.summaryStats || [];
  const launchProfiles = dashboard?.launchProfiles || [];
  const mySessionState = dashboard?.mySessionState || null;
  const queueSnapshot = dashboard?.queueSnapshot || [];
  const activeSessions = dashboard?.activeSessions || [];
  const history = dashboard?.recentSessionHistory || dashboard?.history || [];

  const charts = dashboard?.charts || {};
  const gpuUtilizationSeries = charts.gpuUtilizationSeries || [];
  const queueTrendSeries = charts.queueTrendSeries || [];
  const usageSplit = charts.usageSplit || [];

  const activeQueueItemId = useMemo(() => {
    const mine = queueSnapshot.find((item) => item.mine && ["waiting", "starting", "running"].includes(item.status));
    return mine?.id || null;
  }, [queueSnapshot]);

  const activeSession = useMemo(() => {
    return activeSessions.find((session) => session.mine && ["starting", "running", "idle"].includes(session.status));
  }, [activeSessions]);

  const handleLaunch = async (profileId) => {
    if (!profileId || !accessToken) return;

    setLaunchPending(true);
    setNotice("");
    try {
      const payload = await launchSession(accessToken, profileId);
      setNotice(`Заявка создана: ${payload.requestId}. Позиция: ${payload.queuePosition}`);
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setLaunchPending(false);
    }
  };

  const handleCancelQueue = async () => {
    if (!activeQueueItemId || !accessToken) return;

    setCancelPending(true);
    setNotice("");
    try {
      await cancelQueueItem(accessToken, activeQueueItemId);
      setNotice("Заявка в очереди отменена");
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setCancelPending(false);
    }
  };

  const handleRelaunch = async (sessionId) => {
    if (!sessionId || !accessToken) return;

    setRelaunchingId(sessionId);
    setNotice("");
    try {
      const payload = await relaunchSession(accessToken, sessionId);
      setNotice(`Повторный запуск поставлен в очередь: ${payload.requestId}`);
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setRelaunchingId(null);
    }
  };

  const handleOpenNotebook = async () => {
    if (!accessToken) return;

    const targetSessionId = activeSession?.id || history?.[0]?.id;
    if (!targetSessionId) {
      setError("SESSION_NOT_FOUND: Нет доступной сессии для открытия Notebook");
      return;
    }

    setOpenPending(true);
    setNotice("");
    try {
      const localUrl = getSafeNotebookUrl(activeSession?.notebookUrl);
      if (localUrl) {
        window.open(localUrl, "_blank", "noopener,noreferrer");
      } else {
        const payload = await getSessionAccess(accessToken, targetSessionId);
        const safeNotebookUrl = getSafeNotebookUrl(payload?.notebookUrl);
        if (!safeNotebookUrl) {
          throw new Error("NOTEBOOK_URL_MISSING");
        }
        window.open(safeNotebookUrl, "_blank", "noopener,noreferrer");
      }
      setNotice("Notebook открыт в новой вкладке");
    } catch (err) {
      if (err?.code) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError("SESSION_ACCESS_ERROR: Не удалось получить ссылку на Notebook");
      }
    } finally {
      setOpenPending(false);
    }
  };

  if (loading) {
    return (
      <main className="page-shell">
        <div className="auth-loading">Загрузка панели пользователя...</div>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <header className="page-top">
        <div>
          <h1>Панель пользователя</h1>
          <p>Запускайте Jupyter-сессии, отслеживайте очередь и смотрите загрузку GPU в реальном времени.</p>
          {error ? <p className="inline-error">{error}</p> : null}
          {notice ? <p className="inline-success">{notice}</p> : null}
        </div>
        <Badge tone={connected ? "green" : "yellow"}>{connected ? "Кластер онлайн" : "Переподключение realtime"}</Badge>
      </header>

      <UserSummaryStats stats={summaryStats} />

      <section className="dual-column-layout">
        <SessionLaunchPanel
          profiles={launchProfiles}
          onLaunch={handleLaunch}
          onOpenLast={handleOpenNotebook}
          launchPending={launchPending}
          openPending={openPending}
        />
        <MyQueueCard
          sessionState={mySessionState}
          queueSnapshot={queueSnapshot}
          onCancelQueue={handleCancelQueue}
          onRelaunch={() => handleRelaunch(history?.[0]?.id)}
          cancelPending={cancelPending}
          relaunchPending={Boolean(relaunchingId)}
        />
      </section>

      <section>
        <SectionHeader
          title="Активные сессии"
          subtitle="Текущие сессии пользователя"
          right={<Badge tone="neutral">{activeSessions.length} сессий</Badge>}
        />
        <ActiveSessionsGrid sessions={activeSessions} />
      </section>

      <section>
        <UserChartsPanel gpuData={gpuUtilizationSeries} queueData={queueTrendSeries} usageData={usageSplit} />
      </section>

      <section>
        <SessionHistoryTable items={history} onRelaunch={handleRelaunch} relaunchingId={relaunchingId} />
      </section>
    </main>
  );
}
