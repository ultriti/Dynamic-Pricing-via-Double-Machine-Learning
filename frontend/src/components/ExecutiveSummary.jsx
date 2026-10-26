import React from 'react';

function ExecutiveSummary() {
  return (
    <div style={{ 
      marginTop: '24px', 
      padding: '24px', 
      backgroundColor: '#ffffff', 
      borderRadius: '12px', 
      border: '1px solid #e2e8f0', 
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid #f1f5f9', paddingBottom: '16px', marginBottom: '16px' }}>
        <span style={{ fontSize: '20px' }}>💡</span>
        <h3 style={{ margin: 0, color: '#1e293b', fontSize: '16px', fontWeight: '700', letterSpacing: '0.5px' }}>
          EXECUTIVE INSIGHT
        </h3>
      </div>
      <p style={{ margin: 0, color: '#475569', fontSize: '15px', lineHeight: '1.6' }}>
        By deploying the Double Machine Learning model to target only <strong style={{color: '#7c3aed'}}>"Persuadable"</strong> customers, 
        we project an incremental lift of <strong>2,300 conversions</strong>. 
        This targeted strategy is estimated to save <strong>$4,200</strong> compared to blanket targeting.
      </p>
    </div>
  );
}

export default ExecutiveSummary;