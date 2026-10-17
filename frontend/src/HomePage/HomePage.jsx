import { useState } from 'react';

function HomePage() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [message, setMessage] = useState("");

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'sans-serif' }}>
      
      {/* SIDEBAR */}
      <div style={{ width: '250px', borderRight: '1px solid #e0e0e0', padding: '20px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 'bold' }}>EconoCausal</h2>
        <ul style={{ listStyleType: 'none', padding: 0, marginTop: '30px' }}>
          
          <li 
            onClick={() => setActiveTab('Overview')}
            style={{ padding: '10px', backgroundColor: activeTab === 'Overview' ? '#f3e8ff' : 'transparent', color: activeTab === 'Overview' ? '#6b21a8' : '#666', borderRadius: '8px', marginBottom: '10px', cursor: 'pointer' }}>
            Overview
          </li>
          
          <li 
            onClick={() => setActiveTab('Upload')}
            style={{ padding: '10px', backgroundColor: activeTab === 'Upload' ? '#f3e8ff' : 'transparent', color: activeTab === 'Upload' ? '#6b21a8' : '#666', borderRadius: '8px', marginBottom: '10px', cursor: 'pointer' }}>
            Upload
          </li>
          
          <li 
            onClick={() => setActiveTab('Analysis')}
            style={{ padding: '10px', backgroundColor: activeTab === 'Analysis' ? '#f3e8ff' : 'transparent', color: activeTab === 'Analysis' ? '#6b21a8' : '#666', borderRadius: '8px', marginBottom: '10px', cursor: 'pointer' }}>
            Analysis
          </li>
          
        </ul>
      </div>

      {/* MAIN CONTENT AREA */}
      <div style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
        
        {/* OVERVIEW TAB */}
        {activeTab === 'Overview' && (
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Overview</h1>
            <p style={{ color: '#666', marginBottom: '30px' }}>Dynamic pricing via causal inference</p>

            <div style={{ backgroundColor: '#faf5ff', border: '1px solid #e9d5ff', borderRadius: '16px', padding: '60px 20px', textAlign: 'center', marginBottom: '30px' }}>
              <p style={{ color: '#9333ea', fontSize: '12px', fontWeight: 'bold', letterSpacing: '1px' }}>ANYWHERE & ANYTIME</p>
              <h1 style={{ fontSize: '36px', fontWeight: '900', margin: '10px 0' }}>Estimate Causal<br/>Treatment Effects</h1>
              <p style={{ color: '#666', maxWidth: '500px', margin: '0 auto 20px auto' }}>Upload your e-mail campaign dataset and discover the true impact.</p>
              
              <div style={{ display: 'flex', justifyContent: 'center', gap: '15px' }}>
                <button onClick={() => setMessage("Backend not ready!")} style={{ backgroundColor: '#7c3aed', color: 'white', border: 'none', padding: '12px 24px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Upload dataset</button>
                <button style={{ backgroundColor: 'white', color: 'black', border: '1px solid #ccc', padding: '12px 24px', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>View analysis</button>
              </div>
              {message && <p style={{ color: 'red', marginTop: '10px' }}>{message}</p>}
            </div>

            <div style={{ display: 'flex', gap: '20px' }}>
              <div style={{ flex: 1, border: '1px solid #e0e0e0', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ color: '#ccc', fontSize: '24px', margin: '0 0 10px 0' }}>01</h3>
                <h4 style={{ margin: '0 0 10px 0' }}>Upload CSV</h4>
                <p style={{ color: '#666', fontSize: '14px', margin: 0 }}>Upload the raw dataset. The system validates your schema automatically.</p>
              </div>
              <div style={{ flex: 1, border: '1px solid #e0e0e0', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ color: '#ccc', fontSize: '24px', margin: '0 0 10px 0' }}>02</h3>
                <h4 style={{ margin: '0 0 10px 0' }}>Explore data</h4>
                <p style={{ color: '#666', fontSize: '14px', margin: 0 }}>View distributions, correlations, and summary statistics.</p>
              </div>
              <div style={{ flex: 1, border: '1px solid #e0e0e0', borderRadius: '12px', padding: '20px' }}>
                <h3 style={{ color: '#ccc', fontSize: '24px', margin: '0 0 10px 0' }}>03</h3>
                <h4 style={{ margin: '0 0 10px 0' }}>Causal analysis</h4>
                <p style={{ color: '#666', fontSize: '14px', margin: 0 }}>Estimate treatment effects using DML.</p>
              </div>
            </div>
          </div>
        )}

        {/* UPLOAD TAB (Placeholder for your teammate's code) */}
        {activeTab === 'Upload' && (
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Upload Page</h1>
            <p style={{ color: '#666' }}>Your teammate will build this page here.</p>
          </div>
        )}

        {/* ANALYSIS TAB (Placeholder for your teammate's code) */}
        {activeTab === 'Analysis' && (
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 'bold' }}>Analysis Page</h1>
            <p style={{ color: '#666' }}>Your teammate will build this page here.</p>
          </div>
        )}

      </div>
    </div>
  );
}

export default HomePage;