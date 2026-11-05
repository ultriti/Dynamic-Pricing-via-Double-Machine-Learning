import Plotly from "plotly.js/lib/core";
import createPlotlyComponent from "react-plotly.js/factory";
import bar from "plotly.js/lib/bar";
import histogram from "plotly.js/lib/histogram";
import scatter from "plotly.js/lib/scatter";
import ChartCard from "./ChartCard";

Plotly.register([bar, histogram, scatter]);
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
  const distribution = result.ite_distribution;
  const histogramCenters =
    distribution?.bin_edges.slice(0, -1).map((edge, index) =>
      ((edge + distribution.bin_edges[index + 1]) / 2) * 100,
    ) ?? [];

  return (
    <div className="causal-charts">
      <ChartCard
        title="Out-of-fold Qini curve"
        subtitle="Out-of-sample cumulative lift versus random rollout; shaded 90% stratified-bootstrap band"
      >
        <Plot
          data={[
            {
              x: curve.map((point) => point.population_fraction),
              y: curve.map((point) => point.strategy_gain_lower),
              type: "scatter",
              mode: "lines",
              line: { color: "rgba(79,70,229,0)", width: 0 },
              hoverinfo: "skip",
              showlegend: false,
            },
            {
              x: curve.map((point) => point.population_fraction),
              y: curve.map((point) => point.strategy_gain_upper),
              type: "scatter",
              mode: "lines",
              line: { color: "rgba(79,70,229,0)", width: 0 },
              fill: "tonexty",
              fillcolor: "rgba(79,70,229,0.14)",
              name: "90% bootstrap band",
              hoverinfo: "skip",
            },
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
        title="Distribution of customer ITEs"
        subtitle={
          distribution
            ? `90% interval shown in the table · 5th–95th percentile: ${(distribution.p05 * 100).toFixed(2)} to ${(distribution.p95 * 100).toFixed(2)} pp · extremes: ${(distribution.minimum * 100).toFixed(2)} to ${(distribution.maximum * 100).toFixed(2)} pp`
            : "Final-model customer-level effect estimates"
        }
      >
        {distribution && (
          <Plot
            data={[
              {
                x: histogramCenters,
                y: distribution.counts,
                type: "bar",
                marker: { color: "#6366f1" },
                hovertemplate: "%{x:.2f} pp<br>%{y} customers<extra></extra>",
              },
            ]}
            layout={{
              ...sharedLayout,
              bargap: 0.05,
              xaxis: { title: "Estimated incremental conversion effect (pp)" },
              yaxis: { title: "Customers", rangemode: "tozero" },
            }}
            config={{ responsive: true, displaylogo: false }}
            useResizeHandler
            style={{ width: "100%", height: "340px" }}
          />
        )}
      </ChartCard>
      <ChartCard
        title="Observed uplift by predicted-effect decile"
        subtitle="Out-of-fold conversion rates by predicted-effect decile"
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
