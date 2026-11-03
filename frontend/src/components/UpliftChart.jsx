import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartCard from "./ChartCard";
import { EmptyState } from "./Feedback";

function UpliftChart({ customers }) {
  const estimates = (customers || []).map((customer) => Number(customer.ite))
    .filter(Number.isFinite);
  if (!estimates.length) {
    return <ChartCard title="Estimated ITE distribution"><EmptyState title="No valid model estimates" /></ChartCard>;
  }

  const minimum = Math.min(...estimates);
  const maximum = Math.max(...estimates);
  const binCount = Math.min(12, Math.max(1, Math.ceil(Math.sqrt(estimates.length))));
  const width = maximum === minimum ? 1 : (maximum - minimum) / binCount;
  const bins = Array.from({ length: binCount }, (_, index) => {
    const lower = minimum + index * width;
    return {
      label: maximum === minimum ? lower.toFixed(3) : `${lower.toFixed(3)}–${(lower + width).toFixed(3)}`,
      count: 0,
    };
  });
  estimates.forEach((value) => {
    const index = maximum === minimum
      ? 0
      : Math.min(binCount - 1, Math.floor((value - minimum) / width));
    bins[index].count += 1;
  });

  return (
    <ChartCard title="Estimated ITE distribution" subtitle="Distribution of outputs from the saved model">
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={bins}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tickLine={false} />
            <YAxis allowDecimals={false} tickLine={false} />
            <Tooltip />
            <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}

export default UpliftChart;