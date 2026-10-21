import { Link } from "react-router-dom";
import UpliftChart from "../components/UpliftChart";
import AllocationMatrix from "../components/AllocationMatrix";
import ExecutiveSummary from "../components/ExecutiveSummary";
import './HomePage.css';
function HomePage() {
  return (
    <div style={{ fontFamily: "sans-serif" }}>
      <h1 style={{ fontSize: "24px", fontWeight: "bold" }}>Overview</h1>
      <p style={{ color: "#666", marginBottom: "30px" }}>Dynamic pricing via causal inference</p>




      <div style={{ backgroundColor: "#faf5ff", border: "1px solid #e9d5ff", borderRadius: "16px", padding: "60px 20px", textAlign: "center", marginBottom: "30px" }}>
        <p style={{ color: "#9333ea", fontSize: "12px", fontWeight: "bold", letterSpacing: "1px" }}>ANYWHERE &amp; ANYTIME</p>
        <h2 style={{ fontSize: "36px", fontWeight: "900", margin: "10px 0" }}>Estimate Causal<br />Treatment Effects</h2>
        <p style={{ color: "#666", maxWidth: "500px", margin: "0 auto 20px" }}>Upload your e-mail campaign dataset and discover the true impact.</p>
        <div style={{ display: "flex", justifyContent: "center", gap: "15px" }}>
          <Link to="/upload" style={{ backgroundColor: "#7c3aed", color: "white", padding: "12px 24px", borderRadius: "8px", fontWeight: "bold" }}>Upload dataset</Link>
          <Link to="/eda" style={{ backgroundColor: "white", color: "black", border: "1px solid #ccc", padding: "12px 24px", borderRadius: "8px", fontWeight: "bold" }}>View analysis</Link>
        </div>
      </div>

      <div style={{ display: "flex", gap: "20px" }}>
        {/* Steps */}
        <div className="steps-section">
          <div className="step-card">
            <div className="step-num">01</div>
            <h3>Upload CSV</h3>
            <p>Upload the raw dataset. The system validates your schema automatically.</p>
            <Link to="/upload">Upload a dataset</Link>
          </div>

          <div className="step-card">
            <div className="step-num">02</div>
            <h3>Explore data</h3>
            <p>View distributions, correlations, and summary statistics.</p>
            <Link to="/eda">Explore analysis</Link>
          </div>

          <div className="step-card">
            <div className="step-num">03</div>
            <h3>Causal analysis</h3>
            <p>Estimate treatment effects using DML.</p>
          </div>
        </div>
        {/* Your Chart */}

        <div style={{ marginTop: '40px' }}>
          <UpliftChart />
          <ExecutiveSummary />
          <AllocationMatrix />

        </div>
      </div>
    </div>
  );
}

export default HomePage;
