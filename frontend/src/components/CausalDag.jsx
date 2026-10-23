const nodeStyles = {
  confounder: { fill: "#eff6ff", stroke: "#60a5fa", text: "#1e40af" },
  treatment: { fill: "#fff7ed", stroke: "#fb923c", text: "#9a3412" },
  outcome: { fill: "#f0fdf4", stroke: "#4ade80", text: "#166534" },
};

export default function CausalDag({ nodes, edges }) {
  const positions = Object.fromEntries(
    nodes.map((node, index) => {
      if (node.role === "treatment") {
        return [node.id, { x: 430, y: 205 }];
      }
      if (node.role === "outcome") {
        return [node.id, { x: 650, y: 205 }];
      }
      return [node.id, { x: 105, y: 48 + index * 49 }];
    }),
  );

  return (
    <div className="dag-scroll">
      <svg
        className="causal-dag"
        viewBox="0 0 760 460"
        role="img"
        aria-label="Causal directed acyclic graph with customer confounders, email treatment, and conversion outcome"
      >
        <defs>
          <marker id="dag-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 z" fill="#94a3b8" />
          </marker>
        </defs>
        {edges.map(({ source, target }) => {
          const start = positions[source];
          const end = positions[target];
          const sourceIsFeature = nodes.find((node) => node.id === source)?.role === "confounder";
          return (
            <path
              key={`${source}-${target}`}
              d={
                sourceIsFeature
                  ? `M ${start.x + 69} ${start.y} C 255 ${start.y}, 310 ${end.y}, ${end.x - 70} ${end.y}`
                  : `M ${start.x + 70} ${start.y} L ${end.x - 70} ${end.y}`
              }
              fill="none"
              stroke="#94a3b8"
              strokeWidth="1.3"
              markerEnd="url(#dag-arrow)"
            />
          );
        })}
        {nodes.map((node) => {
          const point = positions[node.id];
          const style = nodeStyles[node.role];
          const width = node.role === "confounder" ? 138 : 142;
          return (
            <g key={node.id}>
              <rect
                x={point.x - width / 2}
                y={point.y - 17}
                width={width}
                height="34"
                rx="8"
                fill={style.fill}
                stroke={style.stroke}
                strokeWidth="1.5"
              />
              <text
                x={point.x}
                y={point.y + 4}
                textAnchor="middle"
                fill={style.text}
                fontSize="12"
                fontWeight="600"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
