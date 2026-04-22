import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function QueueTrendChart({ data }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="fill-queued" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--tone-yellow)" stopOpacity={0.22} />
              <stop offset="100%" stopColor="var(--tone-yellow)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: "var(--text-faint)" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "var(--text-faint)" }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ background: "#0f1a14", border: "1px solid #294632", borderRadius: 8 }} />
          <Area type="monotone" dataKey="queued" name="Пользователи в очереди" stroke="var(--tone-yellow)" fill="url(#fill-queued)" strokeWidth={2} dot={false} />
          <Area type="monotone" dataKey="avgWait" name="Среднее ожидание (мин)" stroke="var(--tone-blue)" fill="none" strokeWidth={2} strokeDasharray="5 4" dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
