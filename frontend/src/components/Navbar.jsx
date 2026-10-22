import { useEffect, useState } from "react";
import { Activity } from "lucide-react";
import { checkApiHealth } from "../services/api";

const Navbar = () => {
  const [connected, setConnected] = useState(null);

  useEffect(() => {
    let active = true;
    const checkHealth = async () => {
      try {
        const health = await checkApiHealth();
        if (active) setConnected(health.status === "healthy");
      } catch {
        if (active) setConnected(false);
      }
    };

    checkHealth();
    const interval = window.setInterval(checkHealth, 15000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <header className="topbar">
      <div>
        <div className="brand-name"><Activity size={19} aria-hidden="true" /> EconoCausal</div>
        <span className="brand-subtitle">Causal Inference Analytics</span>
      </div>
      <div className={`connection-status${connected === false ? " disconnected" : ""}`}>
        <span className="connection-dot" />
        {connected === null ? "Checking API" : connected ? "API connected" : "API unavailable"}
      </div>
    </header>
  );
};

export default Navbar;
