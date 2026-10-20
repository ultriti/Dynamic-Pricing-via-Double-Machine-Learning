function AllocationMatrix({ customers }) {
  const rows = customers.slice(0, 10);

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Model score preview</h2>
          <p>First 10 model outputs. These are not discount allocations or business recommendations.</p>
        </div>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Row</th><th>Treatment group</th><th>Estimated ITE</th><th>Effect (percentage points)</th></tr></thead>
          <tbody>
            {rows.map((customer) => (
              <tr key={customer.row_id}>
                <td>{customer.row_id}</td>
                <td>{customer.treatment_group}</td>
                <td>{Number(customer.ite).toFixed(5)}</td>
                <td>{Number(customer.effect_percentage_points).toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default AllocationMatrix;