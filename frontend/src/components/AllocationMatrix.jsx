import React from 'react';

function AllocationMatrix({ customers }) {
  // Safe fallback in case data isn't loaded yet
  const rows = (customers || []).slice(0, 10);

  return (
    <section className="panel" style={{ marginTop: '30px' }}>
      <div className="panel-heading" style={{ marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>Model score preview</h2>
          <p style={{ fontSize: '14px', color: '#6b7280' }}>First 10 model outputs. These are not discount allocations.</p>
        </div>
      </div>

      <div className="table-scroll" style={{ overflowX: 'auto' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
          <thead>
            <tr style={{ backgroundColor: '#f8fafc', borderBottom: '2px solid #e2e8f0' }}>
              <th style={{ padding: '12px 16px', textAlign: 'left', color: '#475569', fontWeight: '600' }}>Row ID</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', color: '#475569', fontWeight: '600' }}>Treatment Group</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', color: '#475569', fontWeight: '600' }}>Estimated ITE</th>
            </tr>
          </thead>
          <tbody>
            {rows.length > 0 ? (
              rows.map((row, index) => (
                <tr
                  key={row.row_id || index}
                  style={{ borderBottom: '1px solid #e2e8f0', transition: 'background-color 0.2s' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8fafc'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td style={{ padding: '12px 16px', color: '#1e293b' }}>{row.row_id || index}</td>
                  <td style={{ padding: '12px 16px', color: '#1e293b' }}>{row.treatment_group || 'N/A'}</td>
                  <td style={{ padding: '12px 16px', color: '#1e293b' }}>{row.ite ? Number(row.ite).toFixed(4) : '0.0000'}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="3" style={{ padding: '24px', textAlign: 'center', color: '#6b7280' }}>
                  No data available. Please upload a dataset to see previews.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default AllocationMatrix;