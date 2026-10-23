import React from 'react';

function ExecutiveSummary() {
  // In the future, these numbers will come from your Python backend
  const estimatedLift = 2300;
  const estimatedSavings = 4200;

  return (
    <div style={{ 
      marginTop: '30px', 
      padding: '24px', 
      backgroundColor: '#faf5ff', 
      borderRadius: '12px', 
      border: '1px solid #e9d5ff',
      display: 'flex',
      flexDirection: 'column',
      gap: '10px'
    }}>
      <h3 style={{ margin: 0, color: '#6b21a8', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span>💡</span> Executive Summary
      </h3>
      <p style={{ margin: 0, color: '#4c1d95', fontSize: '15px', lineHeight: '1.6' }}>
        By using the Double Machine Learning model to target only <strong>"Persuadable"</strong> customers, 
        we project an incremental lift of <strong>{estimatedLift.toLocaleString()} conversions</strong>. 
        This targeted strategy is estimated to save <strong>${estimatedSavings.toLocaleString()}</strong> compared to blanket targeting.
      </p>
    </div>
  );
}

export default ExecutiveSummary;