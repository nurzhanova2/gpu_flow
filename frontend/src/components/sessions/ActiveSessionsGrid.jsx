import Card from "../ui/Card";
import Badge from "../ui/Badge";
import MeterBar from "../ui/MeterBar";
import StatusBadge from "../ui/StatusBadge";

export default function ActiveSessionsGrid({ sessions }) {
  return (
    <section className="session-grid">
      {sessions.map((session) => (
        <Card key={session.id} className={`session-card ${session.mine ? "session-card-mine" : ""}`}>
          <div className="session-head">
            <div>
              <h4>{session.user}</h4>
              <p>{session.node} - {session.gpu}</p>
            </div>
            <StatusBadge status={session.status} />
          </div>

          <div className="session-meta-row">
            <span><strong>{session.durationMin}м</strong> работы</span>
            <Badge tone="neutral">{session.profile}</Badge>
          </div>

          <div className="session-meters">
            <div>
              <p>GPU</p>
              <MeterBar value={session.gpuUsage} compact tone={session.gpuUsage > 85 ? "red" : session.gpuUsage > 60 ? "yellow" : "green"} />
            </div>
            <div>
              <p>Memory</p>
              <MeterBar value={session.memoryUsage || session.memUsage} compact tone={session.memoryUsage > 80 || session.memUsage > 80 ? "red" : "blue"} />
            </div>
            <div>
              <p>CPU</p>
              <MeterBar value={session.cpuUsage} compact tone={session.cpuUsage > 80 ? "red" : "green"} />
            </div>
          </div>
        </Card>
      ))}
    </section>
  );
}
