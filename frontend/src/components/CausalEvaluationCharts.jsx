import Plotly from "plotly.js/lib/core";
import createPlotlyComponent from "react-plotly.js/factory";
import bar from "plotly.js/lib/bar";
import scatter from "plotly.js/lib/scatter";
import ChartCard from "./ChartCard";

Plotly.register([bar, scatter]);
const Plot = createPlotlyComponent(Plotly);

const sharedLayout = {
  autosize: true,
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "#ffffff",
  font: { family: "Inter, sans-serif", color: "#475569", size: 11 },
  margin: { l: 58, r: 24, t: 18, b: 55 },
  legend: { orientation: "h", y: -0.25 },
};

function CausalEvaluationCharts({ result }) {
  const curve = result.qini_curve ?? [];
  const deciles = result.uplift_by_decile ?? [];

  return (
    <div className="causal-charts">
      <ChartCard
        title="Held-out Qini curve"
        subtitle="Cumulative incremental conversions versus a random rollout"
      >
        <Plot
          data={[
            {
              x: curve.map((point) => point.population_fraction),
              y: curve.map((point) => point.strategy_gain),
              type: "scatter",
              mode: "lines",
              name: "DML targeting",
              line: { color: "#4f46e5", width: 3 },
            },
            {
              x: curve.map((point) => point.population_fraction),
              y: curve.map((point) => point.random_gain),
              type: "scatter",
              mode: "lines",
              name: "Random rollout",
              line: { color: "#94a3b8", width: 2, dash: "dash" },
            },
          ]}
          layout={{
            ...sharedLayout,
            xaxis: { title: "Fraction of customers targeted", tickformat: ".0%", rangemode: "tozero" },
            yaxis: { title: "Estimated incremental conversions", zeroline: true },
          }}
          config={{ responsive: true, displaylogo: false }}
          useResizeHandler
          style={{ width: "100%", height: "340px" }}
        />
      </ChartCard>
      <ChartCard
        title="Observed uplift by predicted-effect decile"
        subtitle="Held-out conversion rates for treatment and control customers"
      >
        <Plot
          data={[
            {
              x: deciles.map((point) => `Decile ${point.decile}`),
              y: deciles.map((point) => point.treated_conversion_rate),
              type: "bar",
              name: "Womens E-Mail",
              marker: { color: "#4f46e5" },
            },
            {
              x: deciles.map((point) => `Decile ${point.decile}`),
              y: deciles.map((point) => point.control_conversion_rate),
              type: "bar",
              name: "No E-Mail",
              marker: { color: "#cbd5e1" },
            },
            {
              x: deciles.map((point) => `Decile ${point.decile}`),
              y: deciles.map((point) => point.observed_uplift),
              type: "scatter",
              mode: "lines+markers",
              name: "Observed uplift",
              yaxis: "y2",
              line: { color: "#16a34a", width: 2 },
            },
          ]}
          layout={{
            ...sharedLayout,
            barmode: "group",
            xaxis: { title: "Customers ranked by DML estimated effect" },
            yaxis: { title: "Conversion rate", tickformat: ".0%", rangemode: "tozero" },
            yaxis2: {
              title: "Observed uplift",
              overlaying: "y",
              side: "right",
              tickformat: ".0%",
              zeroline: true,
            },
          }}
          config={{ responsive: true, displaylogo: false }}
          useResizeHandler
          style={{ width: "100%", height: "340px" }}
        />
      </ChartCard>
    </div>
  );
}

export default CausalEvaluationCharts;
