import React from 'react';

function AllocationMatrix() {
  // Fake data for Week 3
  const users = [
    { id: 'C-1042', segment: 'Womens E-Mail', uplift: 'High', discount: '$15', status: 'Persuadable' },
    { id: 'C-2091', segment: 'Mens E-Mail', uplift: 'Low', discount: '$0', status: 'Sure Thing' },
    { id: 'C-3382', segment: 'No E-Mail', uplift: 'Medium', discount: '$5', status: 'Persuadable' },
    { id: 'C-4811', segment: 'Womens E-Mail', uplift: 'High', discount: '$20', status: 'Persuadable' },
  ];

  return (
    <div style={{ marginTop: '40px', padding: '20px', border: '1px solid #e0e0e0', borderRadius: '12px', backgroundColor: '#fff' }}>
      <h3 style={{ marginBottom: '20px' }}>Allocation Matrix (Week 3 Task)</h3>
      <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e0e0e0' }}>
            <th style={{ padding: '10px' }}>Customer ID</th>
            <th style={{ padding: '10px' }}>Segment</th>
            <th style={{ padding: '10px' }}>Uplift Score</th>
            <th style={{ padding: '10px' }}>Assigned Discount</th>
            <th style={{ padding: '10px' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user, index) => (
            <tr key={index} style={{ borderBottom: '1px solid #f0f0f0' }}>
              <td style={{ padding: '10px' }}>{user.id}</td>
              <td style={{ padding: '10px' }}>{user.segment}</td>
              <td style={{ padding: '10px', color: user.uplift === 'High' ? 'green' : 'orange' }}>{user.uplift}</td>
              <td style={{ padding: '10px', fontWeight: 'bold' }}>{user.discount}</td>
              <td style={{ padding: '10px' }}>
                <span style={{ padding: '4px 8px', borderRadius: '12px', fontSize: '12px', backgroundColor: user.status === 'Persuadable' ? '#e6f4ea' : '#fce8e6', color: user.status === 'Persuadable' ? '#1e8e3e' : '#d93025' }}>
                  {user.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default AllocationMatrix;