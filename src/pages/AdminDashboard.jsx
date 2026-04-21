import { useState } from "react";
import AdminSidebar from "../components/layout/AdminSidebar";
import Badge from "../components/ui/Badge";
import SectionHeader from "../components/ui/SectionHeader";
import AdminKpiGrid from "../components/dashboard/AdminKpiGrid";
import AdminAlerts from "../components/dashboard/AdminAlerts";
import NodeOverviewGrid from "../components/dashboard/NodeOverviewGrid";
import QueueTable from "../components/queue/QueueTable";
import AdminSessionsPanel from "../components/sessions/AdminSessionsPanel";
import AdminChartsPanel from "../components/charts/AdminChartsPanel";
import UserActivityTable from "../components/dashboard/UserActivityTable";
import {
  activeSessionsAdmin,
  adminAlerts,
  adminKpis,
  clusterUsageSeries,
  nodeLoadSeries,
  nodeOverview,
  queueRows,
  userActivityRows,
} from "../data/mockAdminData";

const sectionLabels = {
  overview: "Обзор",
  queue: "Очередь",
  sessions: "Сессии",
  nodes: "Узлы",
  users: "Пользователи",
};

export default function AdminDashboard() {
  const [activeSection, setActiveSection] = useState("overview");

  const queueMetrics = clusterUsageSeries.map((point) => ({
    time: point.time,
    queued: point.queueDepth,
    avgWait: Math.round(8 + point.queueDepth * 1.3),
  }));

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
          </div>
          <Badge tone="green">Раздел: {sectionLabels[activeSection]}</Badge>
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
              <QueueTable rows={queueRows} />
            </section>

            <section>
              <AdminSessionsPanel sessions={activeSessionsAdmin} />
            </section>

            <section>
              <AdminChartsPanel
                clusterData={clusterUsageSeries}
                queueData={queueMetrics}
                nodeLoadData={nodeLoadSeries}
              />
            </section>

            <section>
              <UserActivityTable rows={userActivityRows} />
            </section>
          </>
        ) : null}

        {activeSection === "queue" ? <QueueTable rows={queueRows} /> : null}
        {activeSection === "sessions" ? <AdminSessionsPanel sessions={activeSessionsAdmin} /> : null}
        {activeSection === "nodes" ? <NodeOverviewGrid nodes={nodeOverview} /> : null}
        {activeSection === "users" ? <UserActivityTable rows={userActivityRows} /> : null}
      </main>
    </div>
  );
}
