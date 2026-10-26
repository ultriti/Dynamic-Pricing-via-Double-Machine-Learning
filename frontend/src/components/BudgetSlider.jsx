import React, { useState } from 'react';

function BudgetSlider() {
  const [budget, setBudget] = useState(5000);
  const [customersTargeted, setCustomersTargeted] = useState(0);

  const handleSliderChange = (e) => {
    const newBudget = parseInt(e.target.value);
    setBudget(newBudget);

    // Fake math: Assume each targeted customer costs $15
    const costPerCustomer = 15;
    const targeted = Math.floor(newBudget / costPerCustomer);
    setCustomersTargeted(targeted);
  };

  return (
    <div style={{
      marginTop: '30px',
      padding: '24px',
      backgroundColor: '#fff',
      borderRadius: '12px',
      border: '1px solid #e0e0e0',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)'
    }}>
      <h3 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#1f2937', fontWeight: '600' }}>
        🎯 Budget Optimization
      </h3>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '24px' }}>
        Adjust the campaign budget to dynamically recalculate targeted customers.
      </p>

      {/* The Slider */}
      <input
        type="range"
        min="1000"
        max="20000"
        step="500"
        value={budget}
        onChange={handleSliderChange}
        style={{
          width: '100%',
          cursor: 'pointer',
          accentColor: '#7c3aed',
          height: '6px',
          borderRadius: '4px'
        }}
      />

      <div style={{ display: 'flex', gap: '20px', marginTop: '24px' }}>
        <div style={{ flex: 1, backgroundColor: '#f8fafc', padding: '16px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <span style={{ display: 'block', fontSize: '12px', color: '#64748b', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Allocated Budget</span>
          <span style={{ fontSize: '24px', fontWeight: '700', color: '#0f172a' }}>${budget.toLocaleString()}</span>
        </div>

        <div style={{ flex: 1, backgroundColor: '#f0fdf4', padding: '16px', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
          <span style={{ display: 'block', fontSize: '12px', color: '#15803d', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Customers Targeted</span>
          <span style={{ fontSize: '24px', fontWeight: '700', color: '#14532d' }}>{customersTargeted.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

export default BudgetSlider;