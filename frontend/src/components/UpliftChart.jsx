import React from 'react';
import Plot from 'react-plotly.js';

function UpliftChart() {
  // Fake data for the chart
  const xValues = [0, 1000, 2000, 3000, 4000, 5000];
  const modelCurve = [0, 500, 1200, 1800, 2100, 2300];
  const randomCurve = [0, 300, 600, 900, 1200, 1500];

  return (
    <div style={{ padding: '20px', backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e0e0e0', marginTop: '20px' }}>
      <h3 style={{ marginBottom: '20px' }}>Uplift Curve (Week 2 Task)</h3>
      <Plot
        data={[
          {
            x: xValues,
            y: modelCurve,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Causal Model',
            line: { color: '#7c3aed', width: 3 }
          },
          {
            x: xValues,
            y: randomCurve,
            type: 'scatter',
            mode: 'lines',
            name: 'Random Targeting',
            line: { color: '#ccc', dash: 'dash', width: 2 }
          }
        ]}
        layout={{
          width: 700,
          height: 400,
          xaxis: { title: 'Number of Customers Targeted' },
          yaxis: { title: 'Incremental Conversion' },
          legend: { orientation: 'h', y: -0.2 }
        }}
      />
    </div>
  );
}

export default UpliftChart;