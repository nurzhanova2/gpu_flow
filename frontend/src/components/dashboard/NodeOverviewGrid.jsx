import Badge from "../ui/Badge";
import Card from "../ui/Card";
import MeterBar from "../ui/MeterBar";

export default function NodeOverviewGrid({ nodes }) {
  return (
    <section className="node-grid">
      {nodes.map((node) => {
        const utilization = node.gpuTotal === 0 ? 0 : Math.round((node.gpuUsed / node.gpuTotal) * 100);
        const toneMap = {
          healthy: "green",
          standby: "neutral",
          degraded: "yellow",
          offline: "red",
        };
        const statusTone = toneMap[node.status] || "neutral";
        const statusText = node.status || "unknown";

        return (
          <Card key={node.id} className="node-card">
            <div className="node-card-head">
              <div>
                <h3>{node.hostname}</h3>
                <p>{node.region} - {node.gpuModel}</p>
              </div>
              <Badge tone={statusTone}>{statusText}</Badge>
            </div>

            <div className="node-main-metrics">
              <div>
                <p>GPU</p>
                <strong>{node.gpuUsed}/{node.gpuTotal}</strong>
              </div>
              <div>
                <p>User</p>
                <strong>{node.activeUser || "Free"}</strong>
              </div>
              <div>
                <p>Temp</p>
                <strong>{node.temperature}C</strong>
              </div>
            </div>

            <div className="node-bars">
              <div>
                <span>GPU Utilization</span>
                <MeterBar value={utilization} compact tone={utilization > 80 ? "red" : utilization > 50 ? "yellow" : "green"} />
              </div>
              <div>
                <span>CPU</span>
                <MeterBar value={node.cpu} compact tone={node.cpu > 80 ? "red" : node.cpu > 55 ? "yellow" : "green"} />
              </div>
              <div>
                <span>RAM</span>
                <MeterBar value={node.ram} compact tone={node.ram > 80 ? "red" : node.ram > 60 ? "yellow" : "green"} />
              </div>
            </div>
          </Card>
        );
      })}
    </section>
  );
}
