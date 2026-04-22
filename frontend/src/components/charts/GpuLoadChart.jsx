import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function GpuLoadChart({ data, lines }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer>
        <AreaChart data={data}>
          <defs>
            {lines.map((line) => (
              <linearGradient key={line.id} id={`fill-${line.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={line.color} stopOpacity={0.2} />
                <stop offset="100%" stopColor={line.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: "var(--text-faint)" }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "var(--text-faint)" }} axisLine={false} tickLine={false} domain={[0, 100]} />
          <Tooltip contentStyle={{ background: "#0f1a14", border: "1px solid #294632", borderRadius: 8, color: "#e6efe9" }} />
          {lines.map((line) => (
            <Area
              key={line.id}
              type="monotone"
              dataKey={line.dataKey}
              name={line.label}
              stroke={line.color}
              fill={`url(#fill-${line.id})`}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
