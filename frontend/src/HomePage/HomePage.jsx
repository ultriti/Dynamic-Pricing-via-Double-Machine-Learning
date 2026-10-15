import React from "react";
import { Link } from "react-router-dom";
import "./HomePage.css";

const HomePage = () => {
  return (
    <div className="home">
      <h1 className="page-title">Overview</h1>
      <p className="page-desc">Dynamic pricing via causal inference</p>

      {/* Hero Banner */}
      <div className="hero">
        <span className="hero-tag">Anywhere & Anytime</span>
        <h2>Estimate Causal<br />Treatment Effects</h2>
        <p>
          Upload your e-mail campaign dataset and discover the true impact
          of marketing treatments on customer conversions using Double Machine Learning.
        </p>
        <div className="hero-btns">
          <Link to="/upload" className="btn-gradient">Upload dataset</Link>
          <Link to="/eda" className="btn-outline">View analysis</Link>
        </div>
      </div>

      {/* Steps */}
      <div className="steps-section">
        <div className="step-card">
          <div className="step-num">01</div>
          <h3>Upload CSV</h3>
          <p>Upload the raw Hillstrom dataset. The system validates your schema automatically.</p>
        </div>
        <div className="step-card">
          <div className="step-num">02</div>
          <h3>Explore data</h3>
          <p>View distributions, correlations, segment breakdowns, and summary statistics.</p>
        </div>
        <div className="step-card">
          <div className="step-num">03</div>
          <h3>Causal analysis</h3>
          <p>Estimate treatment effects of email campaigns on conversion using DML.</p>
        </div>
      </div>

      {/* Schema */}
      <div className="schema-card">
        <div className="schema-head">Expected schema</div>
        <div className="schema-scroll">
          <table className="schema-tbl">
            <thead>
              <tr>
                <th>Column</th>
                <th>Role</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>recency</td><td><span className="badge feature">Feature</span></td><td>Months since last purchase</td></tr>
              <tr><td>history</td><td><span className="badge feature">Feature</span></td><td>Dollar value of past purchases</td></tr>
              <tr><td>mens</td><td><span className="badge feature">Feature</span></td><td>Purchased from mens category (0/1)</td></tr>
              <tr><td>womens</td><td><span className="badge feature">Feature</span></td><td>Purchased from womens category (0/1)</td></tr>
              <tr><td>zip_code</td><td><span className="badge feature">Feature</span></td><td>Urban / Suburban / Rural</td></tr>
              <tr><td>newbie</td><td><span className="badge feature">Feature</span></td><td>New customer flag (0/1)</td></tr>
              <tr><td>channel</td><td><span className="badge feature">Feature</span></td><td>Phone / Web / Multichannel</td></tr>
              <tr><td>history_segment</td><td><span className="badge meta">Meta</span></td><td>Binned history ranges</td></tr>
              <tr><td>segment</td><td><span className="badge treatment">Treatment</span></td><td>Mens E-Mail / Womens E-Mail / No E-Mail</td></tr>
              <tr><td>visit</td><td><span className="badge outcome">Outcome</span></td><td>Visited site after campaign (0/1)</td></tr>
              <tr><td>conversion</td><td><span className="badge outcome">Outcome</span></td><td>Made a purchase (0/1)</td></tr>
              <tr><td>spend</td><td><span className="badge outcome">Outcome</span></td><td>Dollar amount spent</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
