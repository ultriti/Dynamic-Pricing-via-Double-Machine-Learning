const formatValue = (value) => {
  if (value === null || value === undefined || value === "") {
    return <span className="missing-value">Missing</span>;
  }
  if (typeof value === "number") return value.toLocaleString();
  return String(value);
};

export default function DataTable({ columns, rows }) {
  if (!columns?.length || !rows?.length) {
    return <p className="muted">No rows to display.</p>;
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatValue(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
