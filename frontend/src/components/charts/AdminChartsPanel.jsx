import { useMemo, useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import GpuLoadChart from "./GpuLoadChart";
import QueueTrendChart from "./QueueTrendChart";

const tabs = [
  { id: "cluster", label: "Утилизация кластера" },
  { id: "queue", label: "Метрики очереди" },
  { id: "nodes", label: "Нагрузка узлов" },
];

export default function AdminChartsPanel({ clusterData, queueData, nodeLoadData }) {
  const [activeTab, setActiveTab] = useState("cluster");

  const chartMeta = useMemo(() => {
    if (activeTab === "cluster") {
      return {
        title: "Утилизация кластера и сессионная активность",
        badge: "24ч",
        content: (
          <GpuLoadChart
            data={clusterData}
            lines={[
              { id: "cluster-gpu", dataKey: "gpuCluster", label: "GPU кластера %", color: "var(--tone-green)" },
              { id: "cluster-active", dataKey: "activeSessions", label: "Активные сессии", color: "var(--tone-blue)" },
            ]}
          />
        ),
      };
    }

    if (activeTab === "queue") {
      return {
        title: "Динамика очереди и среднего ожидания",
        badge: "В реальном времени",
        content: <QueueTrendChart data={queueData} />,
      };
    }

    return {
      title: "Нагрузка по узлам",
      badge: "24ч",
      content: (
        <GpuLoadChart
          data={nodeLoadData}
          lines={[
            { id: "node-alpha", dataKey: "alpha", label: "node-alpha-01", color: "var(--tone-green)" },
            { id: "node-beta", dataKey: "beta", label: "node-beta-02", color: "var(--tone-blue)" },
            { id: "node-gamma", dataKey: "gamma", label: "node-gamma-03", color: "var(--tone-yellow)" },
            { id: "node-epsilon", dataKey: "epsilon", label: "node-epsilon-05", color: "var(--tone-red)" },
          ]}
        />
      ),
    };
  }, [activeTab, clusterData, queueData, nodeLoadData]);

  return (
    <Card>
      <div className="panel-head">
        <h3>{chartMeta.title}</h3>
        <Badge tone="blue">{chartMeta.badge}</Badge>
      </div>

      <div className="chart-tab-row">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeTab === tab.id ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {chartMeta.content}
    </Card>
  );
}
