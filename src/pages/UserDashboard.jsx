import SectionHeader from "../components/ui/SectionHeader";
import Badge from "../components/ui/Badge";
import UserSummaryStats from "../components/dashboard/UserSummaryStats";
import SessionLaunchPanel from "../components/sessions/SessionLaunchPanel";
import MyQueueCard from "../components/queue/MyQueueCard";
import ActiveSessionsGrid from "../components/sessions/ActiveSessionsGrid";
import UserChartsPanel from "../components/charts/UserChartsPanel";
import SessionHistoryTable from "../components/sessions/SessionHistoryTable";
import {
  activeSessions,
  gpuUtilizationSeries,
  launchProfiles,
  mySessionState,
  queueSnapshot,
  queueTrendSeries,
  recentSessionHistory,
  usageSplit,
  userSummaryStats,
} from "../data/mockUserData";

export default function UserDashboard() {
  return (
    <main className="page-shell">
      <header className="page-top">
        <div>
          <h1>Панель пользователя</h1>
          <p>Запускайте Jupyter-сессии, отслеживайте очередь и смотрите загрузку GPU в реальном времени.</p>
        </div>
        <Badge tone="green">Кластер онлайн</Badge>
      </header>

      <UserSummaryStats stats={userSummaryStats} />

      <section className="dual-column-layout">
        <SessionLaunchPanel profiles={launchProfiles} />
        <MyQueueCard sessionState={mySessionState} queueSnapshot={queueSnapshot} />
      </section>

      <section>
        <SectionHeader
          title="Активные сессии"
          subtitle="Текущие сессии по всем узлам кластера"
          right={<Badge tone="neutral">{activeSessions.length} сессий</Badge>}
        />
        <ActiveSessionsGrid sessions={activeSessions} />
      </section>

      <section>
        <UserChartsPanel gpuData={gpuUtilizationSeries} queueData={queueTrendSeries} usageData={usageSplit} />
      </section>

      <section>
        <SessionHistoryTable items={recentSessionHistory} />
      </section>
    </main>
  );
}
