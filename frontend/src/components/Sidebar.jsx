import { BarChart3, Database, LayoutDashboard, Table2, Upload } from "lucide-react";
import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/upload", label: "Upload Dataset", icon: Upload },
  { to: "/eda", label: "Exploratory Analysis", icon: BarChart3 },
  { to: "/preview", label: "Dataset Preview", icon: Table2 },
  { to: "/causal", label: "Model Analysis", icon: Database },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <nav aria-label="Main navigation">
        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}
            end={end}
            key={to}
            to={to}
          >
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-note">
        <strong>Hillstrom dataset</strong>
        <span>Email campaign outcomes; not discount-level experiments.</span>
      </div>
    </aside>
  );
}
