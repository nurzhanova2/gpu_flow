import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AdminSidebar from "../components/layout/AdminSidebar";
import Badge from "../components/ui/Badge";
import SectionHeader from "../components/ui/SectionHeader";
import ActionButton from "../components/ui/ActionButton";
import Modal from "../components/ui/Modal";
import AdminKpiGrid from "../components/dashboard/AdminKpiGrid";
import AdminAlerts from "../components/dashboard/AdminAlerts";
import NodeOverviewGrid from "../components/dashboard/NodeOverviewGrid";
import QueueTable from "../components/queue/QueueTable";
import AdminSessionsPanel from "../components/sessions/AdminSessionsPanel";
import AdminChartsPanel from "../components/charts/AdminChartsPanel";
import UserActivityTable from "../components/dashboard/UserActivityTable";
import {
  blockUser,
  deleteQueueItem,
  getAdminDashboard,
  promoteQueueItem,
  terminateSession,
  unblockUser,
  updateUserLimits,
  warnSession,
} from "../api/dashboardApi";
import { useAuth } from "../context/AuthContext";
import { useRealtime } from "../context/RealtimeContext";

const sectionLabels = {
  overview: "Обзор",
  queue: "Очередь",
  sessions: "Сессии",
  nodes: "Узлы",
  users: "Пользователи",
};
const DEFAULT_WARN_MESSAGE = "Проверьте загрузку и сохраните прогресс";

export default function AdminDashboard() {
  const { accessToken } = useAuth();
  const { subscribe, connected } = useRealtime();
  const reloadTimerRef = useRef(null);

  const [activeSection, setActiveSection] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dashboard, setDashboard] = useState(null);
  const [queuePendingId, setQueuePendingId] = useState(null);
  const [sessionPendingId, setSessionPendingId] = useState(null);
  const [userPendingId, setUserPendingId] = useState(null);
  const [warnDialog, setWarnDialog] = useState({
    open: false,
    sessionId: null,
    message: DEFAULT_WARN_MESSAGE,
  });
  const [limitsDialog, setLimitsDialog] = useState({
    open: false,
    userId: null,
    userName: "",
    maxActiveSessions: "1",
    maxQueuedRequests: "2",
  });

  const loadDashboard = useCallback(async ({ silent = false } = {}) => {
    if (!accessToken) return;

    if (!silent) {
      setLoading(true);
    }

    try {
      const payload = await getAdminDashboard(accessToken);
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
      if (!["queue.updated", "session.updated", "node.updated", "alert.created", "alert.resolved"].includes(event?.event)) return;

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

  const adminKpis = dashboard?.adminKpis || [];
  const adminAlerts = dashboard?.adminAlerts || [];
  const nodeOverview = dashboard?.nodeOverview || [];
  const queueRows = dashboard?.queueRows || [];
  const activeSessionsAdmin = dashboard?.activeSessionsAdmin || [];
  const clusterUsageSeries = dashboard?.clusterUsageSeries || [];
  const nodeLoadSeries = dashboard?.nodeLoadSeries || [];
  const userActivityRows = dashboard?.userActivityRows || [];

  const queueMetrics = useMemo(
    () =>
      clusterUsageSeries.map((point) => ({
        time: point.time,
        queued: point.queueDepth,
        avgWait: Math.round(8 + point.queueDepth * 1.3),
      })),
    [clusterUsageSeries],
  );

  const handlePromoteQueue = async (queueId) => {
    if (!accessToken || !queueId) return;

    setQueuePendingId(queueId);
    setNotice("");
    try {
      await promoteQueueItem(accessToken, queueId);
      setNotice("Элемент очереди поднят");
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setQueuePendingId(null);
    }
  };

  const handleDeleteQueue = async (queueId) => {
    if (!accessToken || !queueId) return;

    setQueuePendingId(queueId);
    setNotice("");
    try {
      await deleteQueueItem(accessToken, queueId);
      setNotice("Элемент очереди удален");
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setQueuePendingId(null);
    }
  };

  const handleWarnSession = async (sessionId) => {
    if (!accessToken || !sessionId) return;
    setWarnDialog({ open: true, sessionId, message: DEFAULT_WARN_MESSAGE });
    setError("");
  };

  const handleWarnDialogSubmit = async () => {
    if (!accessToken || !warnDialog.sessionId) return;
    const cleaned = warnDialog.message.trim();
    if (cleaned.length < 5 || cleaned.length > 500) {
      setError("VALIDATION_ERROR: Сообщение должно быть от 5 до 500 символов");
      return;
    }

    setSessionPendingId(warnDialog.sessionId);
    setNotice("");
    try {
      await warnSession(accessToken, warnDialog.sessionId, cleaned);
      setNotice("Предупреждение отправлено");
      setWarnDialog({ open: false, sessionId: null, message: DEFAULT_WARN_MESSAGE });
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setSessionPendingId(null);
    }
  };

  const handleTerminateSession = async (sessionId) => {
    if (!accessToken || !sessionId) return;

    setSessionPendingId(sessionId);
    setNotice("");
    try {
      await terminateSession(accessToken, sessionId);
      setNotice("Инициировано завершение сессии");
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setSessionPendingId(null);
    }
  };

  const handleToggleBlock = async (row) => {
    if (!accessToken || !row?.id) return;

    setUserPendingId(row.id);
    setNotice("");
    try {
      if (row.status === "blocked") {
        await unblockUser(accessToken, row.id);
        setNotice(`Пользователь ${row.user} разблокирован`);
      } else {
        await blockUser(accessToken, row.id);
        setNotice(`Пользователь ${row.user} заблокирован`);
      }
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setUserPendingId(null);
    }
  };

  const handleUpdateLimits = async (row) => {
    if (!accessToken || !row?.id) return;
    setLimitsDialog({
      open: true,
      userId: row.id,
      userName: row.user,
      maxActiveSessions: String(row.maxActiveSessions || 1),
      maxQueuedRequests: String(row.maxQueuedRequests || 2),
    });
    setError("");
  };

  const handleLimitsSubmit = async () => {
    if (!accessToken || !limitsDialog.userId) return;
    const maxActive = Number(limitsDialog.maxActiveSessions);
    const maxQueued = Number(limitsDialog.maxQueuedRequests);

    if (
      !Number.isInteger(maxActive)
      || maxActive < 1
      || maxActive > 16
      || !Number.isInteger(maxQueued)
      || maxQueued < 1
      || maxQueued > 64
    ) {
      setError("VALIDATION_ERROR: Max active 1..16, max queued 1..64");
      return;
    }

    setUserPendingId(limitsDialog.userId);
    setNotice("");
    try {
      await updateUserLimits(accessToken, limitsDialog.userId, maxActive, maxQueued);
      setNotice(`Лимиты пользователя ${limitsDialog.userName} обновлены`);
      setLimitsDialog({
        open: false,
        userId: null,
        userName: "",
        maxActiveSessions: "1",
        maxQueuedRequests: "2",
      });
      await loadDashboard({ silent: true });
    } catch (err) {
      setError(`${err.code}: ${err.message}`);
    } finally {
      setUserPendingId(null);
    }
  };

  if (loading) {
    return (
      <main className="page-shell">
        <div className="auth-loading">Загрузка панели администратора...</div>
      </main>
    );
  }

  return (
    <div className="admin-layout">
      <AdminSidebar
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        queueCount={queueRows.filter((row) => row.status === "waiting").length}
      />

      <main className="admin-main">
        <header className="page-top">
          <div>
            <h1>Панель администратора</h1>
            <p>Контроль загрузки кластера, управление очередью и мониторинг пользовательских сессий.</p>
            {error ? <p className="inline-error">{error}</p> : null}
            {notice ? <p className="inline-success">{notice}</p> : null}
          </div>
          <div className="admin-status-stack">
            <Badge tone={connected ? "green" : "yellow"}>{connected ? "Realtime online" : "Realtime reconnect"}</Badge>
            <Badge tone="green">Раздел: {sectionLabels[activeSection]}</Badge>
          </div>
        </header>

        {activeSection === "overview" ? (
          <>
            <AdminAlerts alerts={adminAlerts} />
            <AdminKpiGrid items={adminKpis} />

            <section>
              <SectionHeader title="Состояние GPU и узлов" subtitle="Оперативные метрики по вычислительным ресурсам" />
              <NodeOverviewGrid nodes={nodeOverview} />
            </section>

            <section>
              <QueueTable
                rows={queueRows}
                onPromote={handlePromoteQueue}
                onDelete={handleDeleteQueue}
                pendingActionId={queuePendingId}
              />
            </section>

            <section>
              <AdminSessionsPanel
                sessions={activeSessionsAdmin}
                onWarn={handleWarnSession}
                onTerminate={handleTerminateSession}
                pendingActionId={sessionPendingId}
              />
            </section>

            <section>
              <AdminChartsPanel
                clusterData={clusterUsageSeries}
                queueData={queueMetrics}
                nodeLoadData={nodeLoadSeries}
              />
            </section>

            <section>
              <UserActivityTable
                rows={userActivityRows}
                onToggleBlock={handleToggleBlock}
                onUpdateLimits={handleUpdateLimits}
                pendingActionId={userPendingId}
              />
            </section>
          </>
        ) : null}

        {activeSection === "queue" ? (
          <QueueTable
            rows={queueRows}
            onPromote={handlePromoteQueue}
            onDelete={handleDeleteQueue}
            pendingActionId={queuePendingId}
          />
        ) : null}

        {activeSection === "sessions" ? (
          <AdminSessionsPanel
            sessions={activeSessionsAdmin}
            onWarn={handleWarnSession}
            onTerminate={handleTerminateSession}
            pendingActionId={sessionPendingId}
          />
        ) : null}

        {activeSection === "nodes" ? <NodeOverviewGrid nodes={nodeOverview} /> : null}

        {activeSection === "users" ? (
          <UserActivityTable
            rows={userActivityRows}
            onToggleBlock={handleToggleBlock}
            onUpdateLimits={handleUpdateLimits}
            pendingActionId={userPendingId}
          />
        ) : null}
      </main>

      <Modal
        open={warnDialog.open}
        title="Предупреждение для сессии"
        onClose={() => setWarnDialog({ open: false, sessionId: null, message: DEFAULT_WARN_MESSAGE })}
        footer={(
          <>
            <ActionButton
              tone="default"
              onClick={() => setWarnDialog({ open: false, sessionId: null, message: DEFAULT_WARN_MESSAGE })}
            >
              Отмена
            </ActionButton>
            <ActionButton
              tone="primary"
              onClick={handleWarnDialogSubmit}
              disabled={sessionPendingId === warnDialog.sessionId}
            >
              Отправить
            </ActionButton>
          </>
        )}
      >
        <form className="admin-dialog-form" onSubmit={(event) => event.preventDefault()}>
          <label>
            Сообщение пользователю
            <textarea
              value={warnDialog.message}
              onChange={(event) => setWarnDialog((prev) => ({ ...prev, message: event.target.value }))}
              maxLength={500}
              placeholder="Укажите причину предупреждения"
            />
          </label>
        </form>
      </Modal>

      <Modal
        open={limitsDialog.open}
        title="Лимиты пользователя"
        onClose={() =>
          setLimitsDialog({
            open: false,
            userId: null,
            userName: "",
            maxActiveSessions: "1",
            maxQueuedRequests: "2",
          })
        }
        footer={(
          <>
            <ActionButton
              tone="default"
              onClick={() =>
                setLimitsDialog({
                  open: false,
                  userId: null,
                  userName: "",
                  maxActiveSessions: "1",
                  maxQueuedRequests: "2",
                })
              }
            >
              Отмена
            </ActionButton>
            <ActionButton
              tone="primary"
              onClick={handleLimitsSubmit}
              disabled={userPendingId === limitsDialog.userId}
            >
              Сохранить
            </ActionButton>
          </>
        )}
      >
        <form className="admin-dialog-form" onSubmit={(event) => event.preventDefault()}>
          <label>
            Пользователь
            <input type="text" value={limitsDialog.userName} disabled />
          </label>

          <label>
            Max active sessions (1..16)
            <input
              type="number"
              min="1"
              max="16"
              value={limitsDialog.maxActiveSessions}
              onChange={(event) => setLimitsDialog((prev) => ({ ...prev, maxActiveSessions: event.target.value }))}
            />
          </label>

          <label>
            Max queued requests (1..64)
            <input
              type="number"
              min="1"
              max="64"
              value={limitsDialog.maxQueuedRequests}
              onChange={(event) => setLimitsDialog((prev) => ({ ...prev, maxQueuedRequests: event.target.value }))}
            />
          </label>
        </form>
      </Modal>
    </div>
  );
}
