import { Link } from "react-router-dom";

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
        <div style={{ flex: 1, border: "1px solid #e0e0e0", borderRadius: "12px", padding: "20px" }}>
          <h3 style={{ color: "#ccc", fontSize: "24px", margin: "0 0 10px" }}>01</h3>
          <h4 style={{ margin: "0 0 10px" }}>Upload CSV</h4>
          <p style={{ color: "#666", fontSize: "14px", margin: "0 0 12px" }}>Upload the raw dataset. The system validates your schema automatically.</p>
          <Link to="/upload">Upload a dataset</Link>
        </div>
        <div style={{ flex: 1, border: "1px solid #e0e0e0", borderRadius: "12px", padding: "20px" }}>
          <h3 style={{ color: "#ccc", fontSize: "24px", margin: "0 0 10px" }}>02</h3>
          <h4 style={{ margin: "0 0 10px" }}>Explore data</h4>
          <p style={{ color: "#666", fontSize: "14px", margin: "0 0 12px" }}>View distributions, correlations, and summary statistics.</p>
          <Link to="/eda">Explore analysis</Link>
        </div>
        <div style={{ flex: 1, border: "1px solid #e0e0e0", borderRadius: "12px", padding: "20px" }}>
          <h3 style={{ color: "#ccc", fontSize: "24px", margin: "0 0 10px" }}>03</h3>
          <h4 style={{ margin: "0 0 10px" }}>Causal analysis</h4>
          <p style={{ color: "#666", fontSize: "14px", margin: 0 }}>Estimate treatment effects using DML.</p>
        </div>
      </div>
    </div>
  );
}

export default HomePage;
