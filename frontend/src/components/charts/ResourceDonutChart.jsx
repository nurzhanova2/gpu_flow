import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export default function ResourceDonutChart({ data }) {
  return (
    <div className="resource-donut-layout">
      <div className="resource-donut-chart">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" innerRadius={52} outerRadius={76} paddingAngle={2} strokeWidth={0}>
              {data.map((segment) => (
                <Cell key={segment.id} fill={segment.color} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: "#0f1a14", border: "1px solid #294632", borderRadius: 8, color: "#e6efe9" }} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="resource-donut-legend">
        {data.map((segment) => (
          <div key={segment.id}>
            <span style={{ backgroundColor: segment.color }} />
            <p>{segment.label}</p>
            <strong>{segment.value}%</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
