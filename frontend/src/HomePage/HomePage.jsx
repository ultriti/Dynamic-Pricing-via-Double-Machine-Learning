import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Database, Eye, Upload, Users } from "lucide-react";
import UpliftChart from "../components/UpliftChart";
import BudgetSlider from "../components/BudgetSlider";
import AllocationMatrix from "../components/AllocationMatrix";
import ExecutiveSummary from "../components/ExecutiveSummary";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ChartCard from "../components/ChartCard";
import { EmptyState as Empty, ErrorMessage, LoadingSpinner } from "../components/Feedback";
import StatCard from "../components/StatCard";
import { fetchDatasetSummary, getApiErrorMessage } from "../services/api";

function HomePage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await fetchDatasetSummary());
    } catch (requestError) {
      if (requestError.response?.status === 404) {
        setSummary(null);
      } else {
        setError(getApiErrorMessage(requestError));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    fetchDatasetSummary()
      .then((data) => {
        if (active) setSummary(data);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError.response?.status !== 404) {
          setError(getApiErrorMessage(requestError));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const refreshSummary = () => {
    setLoading(true);
    setError(null);
    loadSummary();
  };

  const treatmentGroups = Object.entries(summary?.treatment_group_counts ?? {}).map(
    ([name, customers]) => ({ name, customers }),
  );

  return (
    <div className="page" style={{ backgroundColor: '#f1f5f9', minHeight: '100vh', padding: '32px', fontFamily: 'Inter, system-ui, sans-serif' }}>

      <div style={{ maxWidth: '1300px', margin: '0 auto' }}>

        {/* HEADER */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px' }}>
          <div>
            <h1 style={{ fontSize: '28px', fontWeight: '800', color: '#0f172a', margin: '0 0 8px 0', letterSpacing: '-0.5px' }}>
              Dashboard Overview
            </h1>
            <p style={{ color: '#64748b', fontSize: '15px', margin: 0 }}>
              Monitor your causal inference metrics and customer targeting performance.
            </p>
          </div>
          <Link to="/upload" style={{ display: 'flex', alignItems: 'center', gap: '8px', backgroundColor: '#7c3aed', color: 'white', padding: '10px 20px', borderRadius: '8px', fontWeight: '600', textDecoration: 'none', boxShadow: '0 4px 6px -1px rgba(124, 58, 237, 0.2)' }}>
            <Upload size={18} /> Upload New Dataset
          </Link>
        </div>

        {/* KPI CARDS ROW (Mocked for presentation) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '24px', marginBottom: '32px' }}>

          {/* Card 1 */}
          <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontSize: '14px', fontWeight: '600', color: '#64748b' }}>Total Customers</span>
              <div style={{ backgroundColor: '#f3e8ff', padding: '8px', borderRadius: '8px' }}><Users size={20} color="#7c3aed" /></div>
            </div>
            <h2 style={{ fontSize: '32px', fontWeight: '700', color: '#0f172a', margin: 0 }}>64,000</h2>
            <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: '#16a34a', fontWeight: '500' }}>↑ 12% from last month</p>
          </div>

          {/* Card 2 */}
          <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontSize: '14px', fontWeight: '600', color: '#64748b' }}>Conversion Rate</span>
              <div style={{ backgroundColor: '#dcfce7', padding: '8px', borderRadius: '8px' }}><Eye size={20} color="#16a34a" /></div>
            </div>
            <h2 style={{ fontSize: '32px', fontWeight: '700', color: '#0f172a', margin: 0 }}>0.9%</h2>
            <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: '#16a34a', fontWeight: '500' }}>↑ 0.2% from baseline</p>
          </div>

          {/* Card 3 */}
          <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ fontSize: '14px', fontWeight: '600', color: '#64748b' }}>Estimated Savings</span>
              <div style={{ backgroundColor: '#fef3c7', padding: '8px', borderRadius: '8px' }}><Database size={20} color="#d97706" /></div>
            </div>
            <h2 style={{ fontSize: '32px', fontWeight: '700', color: '#0f172a', margin: 0 }}>$4,200</h2>
            <p style={{ margin: '8px 0 0 0', fontSize: '13px', color: '#16a34a', fontWeight: '500' }}>Based on DML targeting</p>
          </div>
        </div>

        {/* MAIN CONTENT GRID */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '32px' }}>

          {/* LEFT COLUMN (Chart & Table) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

            {/* Executive Summary Card */}
            <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: '700', color: '#1e293b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>💡</span> Executive Insight
              </h3>
              <p style={{ margin: 0, fontSize: '14px', color: '#475569', lineHeight: '1.6' }}>
                By deploying the Double Machine Learning model to target only <strong style={{ color: '#7c3aed' }}>"Persuadable"</strong> customers, we project an incremental lift of <strong>2,300 conversions</strong>. This targeted strategy is estimated to save <strong>$4,200</strong> compared to blanket targeting.
              </p>
            </div>

            {/* Uplift Chart Placeholder */}
            <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', height: '400px', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: '700', color: '#1e293b' }}>Uplift Curve Analysis</h3>
              <div style={{ flex: 1, backgroundColor: '#f8fafc', borderRadius: '8px', border: '1px dashed #cbd5e1', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                [ Your Plotly Uplift Chart Renders Here ]
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN (Budget & Table) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

            {/* Budget Slider Placeholder */}
            <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: '700', color: '#1e293b' }}>🎯 Budget Optimization</h3>
              <input type="range" min="1000" max="20000" style={{ width: '100%', accentColor: '#7c3aed' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '16px' }}>
                <div><span style={{ fontSize: '12px', color: '#64748b' }}>Budget</span><br /><strong style={{ fontSize: '20px' }}>$5,000</strong></div>
                <div style={{ textAlign: 'right' }}><span style={{ fontSize: '12px', color: '#64748b' }}>Targeted</span><br /><strong style={{ fontSize: '20px' }}>333</strong></div>
              </div>
            </div>

            {/* Table Placeholder */}
            <div style={{ backgroundColor: '#ffffff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', flex: 1 }}>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: '700', color: '#1e293b' }}>Top Target Segments</h3>
              <table style={{ width: '100%', fontSize: '13px', textAlign: 'left', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b' }}>
                    <th style={{ paddingBottom: '8px' }}>Customer</th>
                    <th style={{ paddingBottom: '8px' }}>Uplift</th>
                  </tr>
                </thead>
                <tbody>
                  <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '12px 0', color: '#0f172a' }}>C-1042</td>
                    <td style={{ color: '#16a34a', fontWeight: '600' }}>High</td>
                  </tr>
                  <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '12px 0', color: '#0f172a' }}>C-3382</td>
                    <td style={{ color: '#d97706', fontWeight: '600' }}>Med</td>
                  </tr>
                  <tr>
                    <td style={{ padding: '12px 0', color: '#0f172a' }}>C-4811</td>
                    <td style={{ color: '#16a34a', fontWeight: '600' }}>High</td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>
        </div>

        {/* Note for the user since components aren't mounted yet */}
        <div style={{ textAlign: 'center', marginTop: '40px', color: '#94a3b8', fontSize: '12px' }}>
          Live backend integration pending. Displaying mock data for UI presentation.
        </div>

      </div>
    </div>
  );
}

export default HomePage;