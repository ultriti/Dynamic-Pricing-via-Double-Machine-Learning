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
      border: '1px solid #e0e0e0' 
    }}>
      <h3 style={{ margin: '0 0 15px 0', fontSize: '18px' }}>🎯 Budget Optimization</h3>
      <p style={{ color: '#666', fontSize: '14px', marginBottom: '20px' }}>
        Adjust the campaign budget to see how many customers can be targeted.
      </p>

      <input 
        type="range" 
        min="1000" 
        max="20000" 
        step="500" 
        value={budget} 
        onChange={handleSliderChange}
        style={{ width: '100%', cursor: 'pointer', accentColor: '#7c3aed' }}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
        <div style={{ backgroundColor: '#f3e8ff', padding: '10px 20px', borderRadius: '8px' }}>
          <span style={{ display: 'block', fontSize: '12px', color: '#6b21a8', fontWeight: 'bold' }}>Current Budget</span>
          <span style={{ fontSize: '20px', fontWeight: '900', color: '#4c1d95' }}>${budget.toLocaleString()}</span>
        </div>
        
        <div style={{ backgroundColor: '#e6f4ea', padding: '10px 20px', borderRadius: '8px' }}>
          <span style={{ display: 'block', fontSize: '12px', color: '#1e8e3e', fontWeight: 'bold' }}>Customers Targeted</span>
          <span style={{ fontSize: '20px', fontWeight: '900', color: '#137333' }}>{customersTargeted.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

export default BudgetSlider;