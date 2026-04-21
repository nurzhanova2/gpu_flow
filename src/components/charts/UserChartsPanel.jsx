import { useMemo, useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import GpuLoadChart from "./GpuLoadChart";
import QueueTrendChart from "./QueueTrendChart";
import ResourceDonutChart from "./ResourceDonutChart";

const tabs = [
  { id: "gpu", label: "Загрузка GPU" },
  { id: "queue", label: "Тренд очереди" },
  { id: "usage", label: "Распределение ресурсов" },
];

export default function UserChartsPanel({ gpuData, queueData, usageData }) {
  const [activeTab, setActiveTab] = useState("gpu");

  const body = useMemo(() => {
    if (activeTab === "gpu") {
      return (
        <GpuLoadChart
          data={gpuData}
          lines={[
            { id: "user-node-alpha", dataKey: "nodeAlpha", label: "node-alpha-01", color: "var(--tone-green)" },
            { id: "user-node-beta", dataKey: "nodeBeta", label: "node-beta-02", color: "var(--tone-blue)" },
            { id: "user-node-gamma", dataKey: "nodeGamma", label: "node-gamma-03", color: "var(--tone-yellow)" },
          ]}
        />
      );
    }

    if (activeTab === "queue") {
      return <QueueTrendChart data={queueData} />;
    }

    return <ResourceDonutChart data={usageData} />;
  }, [activeTab, gpuData, queueData, usageData]);

  return (
    <Card>
      <div className="panel-head">
        <h3>Аналитика использования</h3>
        <Badge tone="blue">Данные в реальном времени</Badge>
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

      {body}
    </Card>
  );
}
